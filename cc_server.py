#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atrium Command Center — live backend (stdlib only, no pip deps).

Serves the Command Center frontend and a /state endpoint that reads REAL
existing data on this machine:
  - agents      : parsed from ~/agent-reception/agents.js (the product lineup)
  - files       : real files on disk (name, size, mtime) across the Atrium dirs
  - activity    : files modified in the last 48h, mapped to the owning agent
  - cron        : the real Hermes cron jobs (snapshot, refreshed below)
  - calendar    : events (cron-derived daily anchors + standing meetings)
  - relay       : live probe of relay.theatrium.tech (VPS) + localhost:8787

Endpoints:
  GET  /            -> static frontend (index.html)
  GET  /state       -> JSON snapshot above
  POST /chat        -> proxy to the real relay (/chat) — agent souls
  GET  /open?path=  -> os.startfile() click-to-open (never download)

Run:  python cc_server.py 8800
"""
import os, re, json, time, sys, math, sqlite3, urllib.request, urllib.error
import hmac, hashlib, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta
import urllib.parse

HOME = os.path.expanduser("~")
ROOT = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = sys.platform == "win32"

# ---- full-brain sources (Hermes profiles; Windows dev box only) ----
# On the VPS HERMES_PROFILES stays "" and every full-brain layer degrades to
# an empty list — /state keeps working, just without the local brain rings.
HERMES_PROFILES = os.path.join(HOME, "AppData", "Local", "hermes", "profiles") if IS_WINDOWS else ""
HERMES_SHARED_SKILLS = os.path.join(HOME, "AppData", "Local", "hermes", "skills") if IS_WINDOWS else ""
PROFILE_IDS = ["solari-local", "ops-agent", "choppy-agent", "codi-agent", "scribe-agent",
               "writer-agent", "james-agent", "content-agent", "vid-agent"]
PROFILE_LABELS = {
    "solari-local": "Solari1", "ops-agent": "Agent-Ops", "writer-agent": "Writer-Ops",
    "choppy-agent": "Choppy", "scribe-agent": "Scribe", "codi-agent": "Kodi-1",
    "james-agent": "James", "content-agent": "Content", "vid-agent": "Vid",
}

if IS_WINDOWS:
    AGENTS_JS = os.path.join(HOME, "agent-reception", "agents.js")
    # directories that hold the "real existing data" (dev box)
    SCAN_DIRS = [
        os.path.join(HOME, "agent-reception"),
        os.path.join(HOME, "atrium-hosting"),
        os.path.join(HOME, "atrium-companion"),
        os.path.join(HOME, "atrium-command-center"),
        os.path.join(HOME, "ai-agency-research"),
    ]
    # VPS relay is the real brain (marketing site uses the same relay)
    RELAY_CANDIDATES = [
        "https://relay.theatrium.tech",
        "http://127.0.0.1:8787",
    ]
else:
    # VPS / container layout (dirs mounted into the command-center container).
    # NB: bind 0.0.0.0 in main() — Docker port-mapping DNATs to eth0, so a
    # loopback-only bind would be unreachable from the host.
    AGENTS_JS = "/app/agents.js"
    SCAN_DIRS = ["/relay", "/app"]
    # relay lives in a sibling container on the compose network ("relay" DNS name)
    RELAY_CANDIDATES = ["http://relay:8787"]
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "tts_cache", ".research", "assets"}
SKIP_EXT = {".pyc", ".mp3"}

# ---- auth gate (simple PIN/token) ----
# CC_TOKEN env var = the shared secret. If unset, a random token is generated
# and printed once, so the dashboard is never open by default.
# CC_NO_AUTH=1 = LOCAL PREVIEW ONLY (never set on the VPS) — skips the gate so
# headless render/QA can screenshot the dashboard without a session cookie.
CC_TOKEN = os.environ.get("CC_TOKEN", "").strip()
CC_NO_AUTH = os.environ.get("CC_NO_AUTH", "") == "1"
if CC_NO_AUTH:
    print("[auth] CC_NO_AUTH=1 — LOCAL PREVIEW MODE, auth gate DISABLED (never deploy this)")
if not CC_TOKEN:
    CC_TOKEN = secrets.token_urlsafe(16)
    print(f"[auth] CC_TOKEN unset — generated random token: {CC_TOKEN}")
AUTH_COOKIE = "cc_auth"

def _auth_ok(handler):
    return CC_NO_AUTH or _is_authed(handler)

def _session_value():
    return hmac.new(CC_TOKEN.encode(), b"cc-session-v1", hashlib.sha256).hexdigest()

def _cookie_get(cookie_header, name):
    for part in (cookie_header or "").split(";"):
        part = part.strip()
        if part.startswith(name + "="):
            return part[len(name) + 1:]
    return ""

def _is_authed(handler):
    tok = (handler.headers.get("X-Auth-Token") or "").strip()
    if tok and hmac.compare_digest(tok, CC_TOKEN):
        return True
    cookie = _cookie_get(handler.headers.get("Cookie"), AUTH_COOKIE)
    return bool(cookie) and hmac.compare_digest(cookie, _session_value())


# ---- keyword -> agent ownership (for activity + right-panel files) ----
AGENT_FILE_MAP = [
    ("amara",  ["contract", "invoice", "email", "docx", "sop", "followup", "follow-up", "meeting"]),
    ("thabo",  ["research", "market", "pricing", "competitor", "source", "abacus", "oracle", "region", "scan"]),
    ("liam",   ["content", "seo", "blog", "copy", "editorial", "storyboard"]),
    ("naledi", ["support", "success", "faq", "playbook", "buy-in", "onboard", "csat"]),
    ("marcus", ["data", "dashboard", "report", "ops", "ledger", "cashflow", "forecast", "csv", "xlsx"]),
    ("duo",    ["relay", "app", "agent", "code", "build", "deploy", "migrat", "vps", "verify", "watchdog", "script", "payfast", "stripe"]),
]
def file_owner(name):
    n = name.lower()
    for agent, kws in AGENT_FILE_MAP:
        if any(k in n for k in kws):
            return agent
    return "amara"  # default to the EA (general ops)

# ---- agent parsing (from agents.js — the single source of truth) ----
def parse_agents():
    if not os.path.exists(AGENTS_JS):
        return []
    src = open(AGENTS_JS, encoding="utf-8").read()
    m = re.search(r"const AGENTS = \[(.*?)\n\];", src, re.S)
    if not m:
        return []
    body = m.group(1)
    # Split ONLY on top-level agent open braces ("\n  {\n    id:") — the nested
    # avatar object is inline ("avatar: { id: ...") so it is not split.
    parts = re.split(r'\n\s*\{\s*\n\s*id:', body)
    agents = []
    for p in parts[1:]:
        p = "id:" + p  # restore the "id:" the split consumed
        def field(key, default=""):
            mm = re.search(r'\n\s*' + key + r':\s*"([^"]*)"', p)
            return mm.group(1) if mm else default
        mid = re.match(r'id:\s*"([^"]*)"', p)
        aid = mid.group(1) if mid else ""
        skills = []
        sk = re.search(r'\n\s*skills:\s*\[(.*?)\]', p, re.S)
        if sk:
            skills = [s.strip().strip('"') for s in sk.group(1).split('","')]
        voice = re.search(r'voice:\s*\{[^}]*?name:\s*"([^"]*)"', p)
        agents.append({
            "id": aid,
            "name": field("name"),
            "role": field("role"),
            "rate": field("rate"),
            "setup": field("setup"),
            "bio": field("bio"),
            "personality": field("personality"),
            "skills": skills,
            "voice": voice.group(1) if voice else "",
        })
    # receptionist (not in AGENTS[]; defined separately)
    rec = re.search(r'const RECEPTION = \{(.*?)\n\};', src, re.S)
    if rec:
        rb = rec.group(1)
        def rf(key, default=""):
            mm = re.search(r'\n\s*' + key + r':\s*"([^"]*)"', rb)
            return mm.group(1) if mm else default
        rvoice = re.search(r'voice:\s*\{[^}]*?name:\s*"([^"]*)"', rb)
        agents.append({
            "id": "reception", "name": rf("name") or "Atrium Reception",
            "role": rf("role") or "Concierge",
            "rate": "", "setup": "", "bio": rf("greeting"),
            "personality": rf("personality"), "skills": [],
            "voice": rvoice.group(1) if rvoice else "",
        })
    return [a for a in agents if a.get("id") and a.get("name")]

# ---- files + activity (real disk state) ----
# End-user file types ONLY — json/py/js/html/css/yaml/sh etc. are engineering
# internals and are excluded from BOTH the orbit and the sidebar Files list.
END_USER_EXTS = {".md", ".doc", ".docx", ".pdf", ".xlsx", ".xls", ".csv", ".txt",
                 ".pptx", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}
def scan_files():
    files, recent = [], []
    cutoff = time.time() - 48 * 3600
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            rel = os.path.relpath(dirpath, HOME).replace("\\", "/")
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in SKIP_EXT:
                    continue
                if ext not in END_USER_EXTS:
                    continue  # not an end-user file type — keep out of the orbit
                low = fn.lower()
                if any(s in low for s in (".env", "payfast", "auth", "secret", "token", "credential", "password", "google_tts")):
                    continue  # never expose secrets in a live dashboard
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                size = st.st_size
                mtime = st.st_mtime
                owner = file_owner(fn)
                entry = {
                    "name": fn, "dir": rel, "ext": ext.lstrip(".").upper() or "—",
                    "size": size, "mtime": mtime, "owner": owner,
                    "path": p,
                }
                files.append(entry)
                if mtime >= cutoff:
                    recent.append(entry)
    files.sort(key=lambda e: e["mtime"], reverse=True)
    recent.sort(key=lambda e: e["mtime"], reverse=True)
    return files, recent

# ---- security: serve-path guards (repo is PUBLIC — never leak secrets) ----
# Same blocklist as scan_files() above: any path component carrying one of
# these names is refused on /open, /asset and /read BEFORE anything is served.
SECRET_NAME_MARKERS = (".env", "payfast", "auth", "secret", "token",
                       "credential", "password", "google_tts")

def _secret_blocked(p):
    """True if any path component looks secret-ish (case-insensitive)."""
    low = (p or "").replace("\\", "/").lower()
    return any(m in part for part in low.split("/") for m in SECRET_NAME_MARKERS)

def _safe_resolve(p, allowed):
    """Resolve p to its realpath iff it stays inside one of `allowed` roots.
    Rejects empty paths, '..' components, absolute escapes and symlink
    escapes (fail closed: any error -> None)."""
    if not p:
        return None
    if any(part == ".." for part in p.replace("\\", "/").split("/")):
        return None
    try:
        ap = os.path.realpath(os.path.abspath(p))
    except Exception:
        return None
    nap = os.path.normcase(ap)
    for d in allowed:
        try:
            nrd = os.path.normcase(os.path.realpath(d))
        except Exception:
            continue
        if nap == nrd or nap.startswith(nrd + os.sep):
            return ap
    return None

# ---- cron (real Hermes jobs, snapshot from `cronjob list` 2026-08-16) ----
CRON_JOBS = [
    {"name": "Multica board watcher",        "schedule": "every 60m",  "on": True},
    {"name": "PHI-Zone stack watchdog",      "schedule": "every 5m",   "on": True},
    {"name": "Hourly Token Usage",           "schedule": "0 * * * *",  "on": True},
    {"name": "Quro claims watch",            "schedule": "every 30m",  "on": True},
    {"name": "Atrium watchdog",              "schedule": "every 15m",  "on": True},
    {"name": "Nightly Atrium state export",  "schedule": "30 2 * * *", "on": True},
    {"name": "VPS migration daily nudge",    "schedule": "30 7 * * *", "on": True},
]

# ---- calendar: standing events + cron-derived daily anchors ----
def calendar_events():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    ev = {
        today: [
            ["07:00", "Daily brief (agent plan)"],
            ["07:30", "Migration nudge"],
            ["18:00", "Evening scorecard"],
        ]
    }
    # standing meetings (Aug 2026)
    ev["2026-08-17"] = [["10:00", "First-customer kickoff"], ["15:00", "Stripe live check"]]
    ev["2026-08-18"] = [["11:00", "Quro stockroom audit"]]
    return ev

# ---- Obsidian vault (AI OS second brain) ----
# Karpathy RAG layout: raw/ (unstructured) -> wiki/ (structured) -> outputs/
# (deliverables), plus runs/ (loop-engineering logs) and ops/ (directives,
# briefs). Every level carries an index.md map so agents + the dashboard can
# navigate cheaply. VAULT is mounted at /vault on the VPS.
VAULT = "/vault" if not IS_WINDOWS else os.path.join(HOME, "atrium-vault")
ZONES = {
    "raw":     {"label": "RAW",     "color": "#C98A5E"},
    "wiki":    {"label": "WIKI",    "color": "#CDA526"},
    "outputs": {"label": "OUTPUTS", "color": "#8FA98A"},
    "runs":    {"label": "RUNS",    "color": "#8E9AB2"},
    "ops":     {"label": "OPS",     "color": "#C6B3BB"},
}
INDEX_COLOR = "#E8CFA0"

# ---- vector-search cache for vault ----
EMB_DIR = os.path.join(HOME, ".atrium")
EMB_CACHE_FILE = os.path.join(EMB_DIR, "embeddings.json")
EMB_MODEL = "qwen3-embedding:0.6b"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MAX_EMBED_CHARS = 6000

def _load_emb_cache():
    try:
        if os.path.isfile(EMB_CACHE_FILE):
            with open(EMB_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_emb_cache(cache):
    try:
        os.makedirs(EMB_DIR, exist_ok=True)
        with open(EMB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception as e:
        print("[search] could not save embedding cache:", e)

def _embed_with_ollama(texts, batch_size=3):
    """Embed a list of texts via Ollama /api/embed in small batches. Returns list of vectors."""
    out = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        body = json.dumps({"model": EMB_MODEL, "input": chunk}).encode()
        req = urllib.request.Request(
            OLLAMA_HOST + "/api/embed",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Atrium-CC/1.0"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode())
            embs = d.get("embeddings")
            if not embs or len(embs) != len(chunk):
                raise RuntimeError("Ollama returned unexpected embedding shape")
            out.extend(embs)
    return out

def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)

def _read_text(path, limit=MAX_EMBED_CHARS):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except Exception:
        return ""

def _vault_md_files():
    if not os.path.isdir(VAULT):
        return []
    files = []
    for dirpath, dirnames, filenames in os.walk(VAULT):
        dirnames[:] = [x for x in dirnames if x not in (".obsidian", ".git", ".trash", "node_modules", "__pycache__")]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                rel = os.path.relpath(p, VAULT).replace("\\", "/")
                zone = _zone_of(rel)
                title, preview = read_md_preview(p, limit=300)
                files.append({
                    "path": p, "rel": rel, "name": title or fn, "zone": zone,
                    "mtime": st.st_mtime, "preview": preview,
                })
    return files

def _keyword_fallback(docs, q):
    qtoks = [t for t in q.lower().split() if len(t) > 2]
    out = []
    for d in docs:
        hay = (d["name"] + " " + d["preview"]).lower()
        score = sum(1 for t in qtoks if t in hay)
        if score:
            out.append({
                "path": d["path"], "name": d["name"], "zone": d["zone"],
                "type": "memory", "node_id": "mem:" + d["path"],
                "score": round(score / max(len(qtoks), 1), 3),
                "snippet": d["preview"][:240],
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:5]

# ---- whole-brain search helpers (profiles / sessions / skills / memories / files) ----
def _fts_match_query(q):
    """Turn free text into an FTS5 AND-of-quoted-phrases query (quote-safe)."""
    toks = [t.strip('"') for t in q.split() if t.strip()]
    toks = [t for t in toks if len(t) >= 3]
    if not toks:
        return ""
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in toks)

def _search_sessions(q, brain):
    """FTS5 across every profile state.db -> conversation results (cap 10)."""
    out = []
    fts = _fts_match_query(q)
    if not fts or not HERMES_PROFILES:
        return out
    by_prof = {}
    for s in brain["sessions"]:
        by_prof.setdefault(s["profile"], {})[s["session_id"]] = s
    for pid in PROFILE_IDS:
        db = os.path.join(HERMES_PROFILES, pid, "state.db")
        if not os.path.isfile(db):
            continue
        try:
            con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
            cur = con.cursor()
            rows = cur.execute(
                "SELECT m.session_id, m.content, m.role FROM messages_fts "
                "JOIN messages m ON messages_fts.rowid = m.id "
                "WHERE messages_fts MATCH ? LIMIT 8", (fts,)).fetchall()
            con.close()
        except Exception:
            continue
        for sid, content, role in rows:
            sess = by_prof.get(pid, {}).get(sid)
            name = sess["title"] if sess else sid
            out.append({
                "type": "conversation", "node_id": "conv:" + pid + ":" + sid,
                "name": name, "zone": pid, "score": 0.9,
                "snippet": (content or "")[:160],
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:10]

def _search_skills(q, brain):
    toks = [t.lower() for t in q.split() if len(t) > 2]
    out = []
    for sk in brain["skills"]:
        hay = ((sk["name"] or "") + " " + (sk["desc"] or "")).lower()
        score = sum(1 for t in toks if t in hay)
        if score:
            out.append({
                "type": "skill", "node_id": "skill:" + sk["profile"] + ":" + sk["name"],
                "name": sk["name"], "zone": "skills",
                "score": round(score / max(len(toks), 1), 3),
                "snippet": (sk["desc"] or "")[:160],
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:5]

def _search_profile_memories(q, brain):
    toks = [t.lower() for t in q.split() if len(t) > 2]
    out = []
    for m in brain["pmem"]:
        txt = _read_text(m["path"], 6000)
        hay = (m["name"] + " " + txt).lower()
        score = sum(1 for t in toks if t in hay)
        if score:
            nm = m["name"].split(".")[0]
            out.append({
                "type": "memory", "node_id": "pmem:" + m["profile"] + ":" + nm,
                "name": _humanize_profile(m["profile"]) + " · " + nm,
                "zone": m["profile"], "score": round(score / max(len(toks), 1), 3),
                "snippet": txt[:160],
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:5]

def _search_files(q):
    toks = [t.lower() for t in q.split() if len(t) > 2]
    out = []
    files, _ = scan_files()
    for f in files:
        hay = ((f["name"] or "") + " " + (f["dir"] or "")).lower()
        score = sum(1 for t in toks if t in hay)
        if score:
            out.append({
                "type": "file", "node_id": "file:" + f["path"],
                "name": f["name"], "zone": "files",
                "score": round(score / max(len(toks), 1), 3),
                "snippet": f["dir"] + " · " + f["ext"],
            })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:5]

def search_vault(q):
    q = (q or "").strip()
    if not q:
        return {"query": "", "results": [], "model": EMB_MODEL, "mode": "empty"}
    docs = _vault_md_files()
    vault_res, mode = [], "no_docs"
    if docs:
        cache = _load_emb_cache()
        to_embed = []
        to_embed_idx = []
        for i, d in enumerate(docs):
            c = cache.get(d["path"])
            if c and c.get("mtime") == d["mtime"] and isinstance(c.get("vec"), list) and len(c["vec"]) > 10:
                d["vec"] = c["vec"]
            else:
                d["vec"] = None
                to_embed.append(_read_text(d["path"], MAX_EMBED_CHARS) or d["preview"])
                to_embed_idx.append(i)
        if to_embed:
            try:
                embs = _embed_with_ollama(to_embed)
                for j, idx in enumerate(to_embed_idx):
                    docs[idx]["vec"] = embs[j]
                    cache[docs[idx]["path"]] = {"mtime": docs[idx]["mtime"], "vec": embs[j]}
                _save_emb_cache(cache)
            except Exception as e:
                print("[search] Ollama embed failed, using keyword fallback:", e)
                vault_res = _keyword_fallback(docs, q)
                mode = "keyword"
        if not vault_res:
            try:
                qemb = _embed_with_ollama([q])[0]
            except Exception as e:
                print("[search] Ollama query embed failed, using keyword fallback:", e)
                vault_res = _keyword_fallback(docs, q)
                mode = "keyword"
            if not vault_res:
                out = []
                for d in docs:
                    v = d.get("vec")
                    if not v:
                        continue
                    score = _cosine(qemb, v)
                    if score > 0.0:
                        out.append({
                            "path": d["path"], "name": d["name"], "zone": d["zone"],
                            "type": "memory", "node_id": "mem:" + d["path"],
                            "score": round(score, 4), "snippet": d["preview"][:240],
                        })
                out.sort(key=lambda x: x["score"], reverse=True)
                vault_res = out[:5]
                mode = "vector"

    # whole-brain merge: sessions + skills + profile memories + files
    try:
        brain = profile_brain()
    except Exception:
        brain = {"profiles": [], "sessions": [], "skills": [], "pmem": []}
    merged = vault_res + _search_sessions(q, brain) + _search_skills(q, brain) \
        + _search_profile_memories(q, brain) + _search_files(q)
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)
    if mode == "no_docs" and merged:
        mode = "keyword"
    return {"query": q, "results": merged[:12], "model": EMB_MODEL, "mode": mode}

_START = time.time()
_MEMORY_CACHE = {"t": 0.0, "data": None}

def _zone_of(rel):
    top = rel.split(os.sep)[0] if os.sep in rel else rel
    if top in ZONES:
        return top
    if top.lower() == "index.md":
        return "index"
    return "ops"

def read_md_preview(path, limit=600):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            txt = fh.read(20000)
    except OSError:
        return os.path.basename(path), ""
    title = ""
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    if m:
        title = m.group(1).strip()
    if not title:
        title = os.path.basename(path)
    body = re.sub(r"^#.*$", "", txt, flags=re.M).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    return title, body[:limit]

def build_memory():
    now = time.time()
    if _MEMORY_CACHE["data"] is not None and now - _MEMORY_CACHE["t"] < 60:
        return _MEMORY_CACHE["data"]
    empty = {"zones": {z: {"count": 0, "files": []} for z in ZONES},
             "nodes": [], "edges": [], "total": 0, "brief": {},
             "velocity": {"day": 0, "week": 0}, "root": VAULT}
    if not os.path.isdir(VAULT):
        _MEMORY_CACHE.update({"t": now, "data": empty})
        return empty
    zones = {z: {"count": 0, "files": []} for z in ZONES}
    nodes, edges, seen = [], [], set()
    day_cut = now - 86400; week_cut = now - 7 * 86400
    vel_day = vel_week = 0
    MEM_EXTS = {".md", ".txt", ".json", ".csv", ".py", ".html", ".docx", ".xlsx", ".pdf"}
    for dirpath, dirnames, filenames in os.walk(VAULT):
        dirnames[:] = [x for x in dirnames if x not in (".obsidian", ".git", ".trash", "node_modules", "__pycache__")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() not in MEM_EXTS:
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            nid = "mem:" + p
            if nid in seen:
                continue
            seen.add(nid)
            is_index = fn.lower() == "index.md"
            zone = _zone_of(os.path.relpath(dirpath, VAULT))
            title, preview = read_md_preview(p) if fn.lower().endswith(".md") else (fn, "")
            entry = {"id": nid, "type": "memory", "zone": zone, "index": is_index,
                     "label": fn, "title": title, "path": p,
                     "rel": os.path.relpath(p, VAULT).replace("\\", "/"),
                     "mtime": st.st_mtime, "size": st.st_size, "preview": preview}
            nodes.append(entry)
            if is_index:
                zones.setdefault("index", {"count": 0, "files": []})
                zones["index"]["count"] += 1
                zones["index"]["files"].append(entry)
            else:
                zones[zone]["count"] += 1
                zones[zone]["files"].append(entry)
                if st.st_mtime >= day_cut: vel_day += 1
                if st.st_mtime >= week_cut: vel_week += 1
    # index maps: [[wikilink]] edges from index.md + wiki articles
    base_ids = {}
    for n in nodes:
        base_ids[n["label"].lower()] = n["id"]
        base_ids[(n["title"] or "").lower()] = n["id"]
    for n in nodes:
        if not (n["index"] or n["zone"] == "wiki"):
            continue
        try:
            txt = open(n["path"], encoding="utf-8", errors="ignore").read(20000)
        except OSError:
            continue
        for m in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", txt):
            tgt = base_ids.get(m.group(1).strip().lower())
            if tgt and tgt != n["id"]:
                edges.append({"source": n["id"], "target": tgt,
                              "kind": "maps" if n["index"] else "refs"})
    brief = {}
    wikis = [n for n in nodes if n["zone"] == "wiki" and not n["index"]]
    runs = [n for n in nodes if n["zone"] == "runs" and not n["index"]]
    if wikis:
        w = max(wikis, key=lambda n: n["mtime"])
        brief["wiki"] = {"title": w["title"], "preview": w["preview"],
                         "path": w["path"], "rel": w["rel"]}
    if runs:
        r = max(runs, key=lambda n: n["mtime"])
        brief["run"] = {"title": r["title"], "preview": r["preview"],
                        "path": r["path"], "rel": r["rel"]}
    data = {"zones": zones, "nodes": nodes, "edges": edges, "total": len(nodes),
            "brief": brief, "velocity": {"day": vel_day, "week": vel_week},
            "root": VAULT}
    _MEMORY_CACHE.update({"t": now, "data": data})
    return data

def build_directives():
    """Top directives — read from vault/ops/directives.md (seeded from the
    real Multica board so the dashboard never invents priorities)."""
    p = os.path.join(VAULT, "ops", "directives.md")
    items = []
    if os.path.isfile(p):
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
            for line in txt.splitlines():
                s = line.strip()
                m = re.match(r"^- \[( |x)\]\s*(.+)$", s)
                if m:
                    items.append({"text": m.group(2).strip(), "done": m.group(1) == "x"})
        except OSError:
            pass
    return items[:6]

def read_preview(path):
    """Bounded text preview for the right panel (auth-gated; vault/scan dirs only)."""
    allowed = SCAN_DIRS + [ROOT, VAULT]
    if HERMES_PROFILES:
        allowed += [HERMES_PROFILES]
    if HERMES_SHARED_SKILLS:
        allowed += [HERMES_SHARED_SKILLS]
    ap = _safe_resolve(path, allowed)
    if ap is None or _secret_blocked(ap) or not os.path.isfile(ap):
        return None
    if os.path.splitext(ap)[1].lower() not in TEXT_EXTS:
        return {"path": ap, "text": "", "binary": True}
    try:
        with open(ap, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read(40000)
    except OSError:
        return None
    return {"path": ap, "text": text, "binary": False}

# ---- relay probe ----
def probe_relay():
    vps = local = False
    vps_agents = 0
    try:
        req = urllib.request.Request(RELAY_CANDIDATES[0] + "/health")
        req.add_header("User-Agent", "Atrium-CC/1.0")
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read().decode())
            vps = d.get("status") == "ok"
            vps_agents = d.get("agents", 0)
    except Exception:
        vps = False
    local_probe = "http://127.0.0.1:8787" if IS_WINDOWS else "http://relay:8787"
    try:
        with urllib.request.urlopen(local_probe + "/health", timeout=2) as r:
            local = r.status == 200
    except Exception:
        local = False
    return {"vps": vps, "vps_agents": vps_agents, "local": local,
            "url": RELAY_CANDIDATES[0]}

# ---- knowledge graph (real: agents + files + content-derived links) ----
TEXT_EXTS = {".md", ".py", ".js", ".json", ".html", ".css", ".txt", ".csv", ".yml", ".yaml", ".sh"}

def read_text_bounded(path, limit=40000):
    if os.path.splitext(path)[1].lower() not in TEXT_EXTS:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except OSError:
        return None

# =====================================================================
# FULL-BRAIN LAYER — every Hermes profile on this machine: sessions,
# skills and profile memories (Windows only; degrades to [] on the VPS).
# Every scanner is wrapped so a corrupt/locked DB can never break /state.
# =====================================================================
_PROFILE_CACHE = {"t": 0.0, "data": None}

def _profile_db(profile_dir):
    return os.path.join(profile_dir, "state.db")

def scan_sessions(profile_dir, profile):
    """Read a profile's state.db (READ-ONLY, live-written DB) -> session list."""
    out = []
    db = _profile_db(profile_dir)
    if not os.path.isfile(db):
        return out
    try:
        con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        rows = cur.execute(
            "SELECT id, display_name, session_key, model, message_count, started_at, "
            "last_activity_at, source, chat_type, title FROM sessions "
            "ORDER BY COALESCE(last_activity_at, started_at) DESC LIMIT 300"
        ).fetchall()
        # first user message per session (title + preview fallbacks)
        first_msgs = {}
        try:
            for r in cur.execute(
                "SELECT m.session_id, m.content FROM messages m "
                "WHERE m.role='user' AND m.content!='' AND m.id = "
                "(SELECT MIN(m2.id) FROM messages m2 WHERE m2.session_id=m.session_id "
                " AND m2.role='user' AND m2.content!='')"):
                first_msgs[r[0]] = r[1]
        except Exception:
            pass
        for r in rows:
            sid = r["id"]
            first = (first_msgs.get(sid) or "").strip()
            title = ((r["display_name"] or "").strip() or (r["title"] or "").strip()
                     or (r["session_key"] or "").strip() or first[:40].strip())
            if not title:
                st = r["last_activity_at"] or r["started_at"] or 0
                title = ("Session " + time.strftime("%Y-%m-%d", time.localtime(st))) if st else "Session"
            out.append({
                "profile": profile, "session_id": sid, "title": title[:80],
                "model": r["model"] or "", "message_count": r["message_count"] or 0,
                "last_ts": r["last_activity_at"] or r["started_at"] or 0,
                "source": r["source"] or "", "chat_type": r["chat_type"] or "",
                "preview": first[:160],
            })
        con.close()
    except Exception as e:
        print("[profiles] scan_sessions failed for", profile, ":", e)
    return out

def scan_skills(profile_dir, profile, skills_root=None):
    """Walk <profile>/skills/** for SKILL.md files (or an explicit skills_root)."""
    out = []
    root = skills_root if skills_root is not None else os.path.join(profile_dir, "skills")
    if not os.path.isdir(root):
        return out
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if x != ".git"]
            if "SKILL.md" not in filenames:
                continue
            p = os.path.join(dirpath, "SKILL.md")
            parent = os.path.basename(dirpath)
            grand = os.path.basename(os.path.dirname(dirpath)) or ""
            desc = ""
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    head = fh.read(4000)
                m = re.search(r"^description:\s*(.+)$", head, re.M)
                if m:
                    desc = m.group(1).strip()[:120]
            except OSError:
                pass
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append({"profile": profile, "name": parent, "category": grand,
                        "path": p, "mtime": st.st_mtime, "desc": desc})
    except Exception as e:
        print("[profiles] scan_skills failed for", profile, ":", e)
    return out

def scan_profile_memories(profile_dir, profile):
    """<profile>/memories/MEMORY.md + USER.md (the agent's persistent memory)."""
    out = []
    mem_dir = os.path.join(profile_dir, "memories")
    if not os.path.isdir(mem_dir):
        return out
    try:
        for name in ("MEMORY.md", "USER.md"):
            p = os.path.join(mem_dir, name)
            if not os.path.isfile(p):
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append({"profile": profile, "name": name, "path": p,
                        "mtime": st.st_mtime, "size": st.st_size})
    except Exception as e:
        print("[profiles] scan_profile_memories failed for", profile, ":", e)
    return out

def scan_profiles():
    """{id, dir, session_count, message_count, memory_count, skill_count, last_ts} per profile."""
    out = []
    if not HERMES_PROFILES or not os.path.isdir(HERMES_PROFILES):
        return out
    for pid in PROFILE_IDS:
        d = os.path.join(HERMES_PROFILES, pid)
        if not os.path.isdir(d):
            continue
        try:
            sessions = scan_sessions(d, pid)
            skills = scan_skills(d, pid)
            mems = scan_profile_memories(d, pid)
            out.append({
                "id": pid, "dir": d,
                "session_count": len(sessions),
                "message_count": sum(s["message_count"] for s in sessions),
                "memory_count": len(mems),
                "skill_count": len(skills),
                "last_ts": max([s["last_ts"] or 0 for s in sessions] + [0]),
            })
        except Exception as e:
            print("[profiles] scan_profiles failed for", pid, ":", e)
    return out

def profile_brain():
    """Cached (60s) full-brain scan: profiles + sessions + skills + profile memories."""
    now = time.time()
    if _PROFILE_CACHE["data"] is not None and now - _PROFILE_CACHE["t"] < 60:
        return _PROFILE_CACHE["data"]
    data = {"profiles": [], "sessions": [], "skills": [], "pmem": []}
    try:
        for p in scan_profiles():
            data["profiles"].append(p)
            data["sessions"].extend(scan_sessions(p["dir"], p["id"]))
            data["skills"].extend(scan_skills(p["dir"], p["id"]))
            data["pmem"].extend(scan_profile_memories(p["dir"], p["id"]))
        if HERMES_SHARED_SKILLS and os.path.isdir(HERMES_SHARED_SKILLS):
            data["skills"].extend(scan_skills("", "shared", HERMES_SHARED_SKILLS))
    except Exception as e:
        print("[profiles] profile_brain failed:", e)
    _PROFILE_CACHE.update({"t": now, "data": data})
    return data

def _humanize_profile(pid):
    return PROFILE_LABELS.get(pid, pid.replace("-", " ").title())

def read_conversation(profile, sid):
    """Read-only transcript tail for /conv (auth-gated). Returns None on bad params."""
    if not HERMES_PROFILES or not profile or not sid or profile not in PROFILE_IDS:
        return None
    db = _profile_db(os.path.join(HERMES_PROFILES, profile))
    if not os.path.isfile(db):
        return None
    try:
        con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        s = cur.execute(
            "SELECT id, display_name, session_key, model, message_count, started_at, "
            "last_activity_at, source, chat_type, title FROM sessions WHERE id=?",
            (sid,)).fetchone()
        if not s:
            con.close()
            return None
        msgs = cur.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 12",
            (sid,)).fetchall()
        con.close()
        msgs = msgs[::-1]
        name = ((s["display_name"] or "").strip() or (s["title"] or "").strip()
                or (s["session_key"] or "").strip() or "Session")
        return {
            "name": name[:80], "model": s["model"] or "",
            "message_count": s["message_count"] or 0,
            "last_ts": s["last_activity_at"] or s["started_at"] or 0,
            "source": s["source"] or "", "chat_type": s["chat_type"] or "",
            "messages": [{"role": m["role"] or "", "content": (m["content"] or "")[:500]}
                         for m in msgs],
        }
    except Exception as e:
        print("[conv] read_conversation failed:", e)
        return None

_GRAPH_CACHE = {"t": 0.0, "data": None}
def build_graph(files, agents):
    now = time.time()
    if _GRAPH_CACHE["data"] is not None and now - _GRAPH_CACHE["t"] < 60:
        return _GRAPH_CACHE["data"]

    nodes = []
    for a in agents:
        nodes.append({"id": "agent:" + a["id"], "type": "agent", "label": a["name"],
                      "agent": a["id"], "owner": None, "role": a["role"], "rate": a["rate"]})
    # file nodes (id by full path — unique) + basename -> [ids] for reference linking
    path_id, basename_ids = {}, {}
    for f in files:
        fid = "file:" + str(f["path"])
        path_id[f["path"]] = fid
        basename_ids.setdefault(f["name"].lower(), []).append(fid)
        nodes.append({"id": fid, "type": "file", "label": f["name"], "owner": f["owner"],
                      "path": f["path"], "ext": f["ext"], "size": f["size"], "mtime": f["mtime"]})

    # agent name tokens (full name + first/last words) for mention detection
    agent_tokens = {}
    for a in agents:
        toks = set()
        nm = (a.get("name") or "").lower()
        if nm:
            toks.add(nm)
        for w in nm.split():
            if len(w) > 2:
                toks.add(w)
        agent_tokens[a["id"]] = toks

    basenames = set(basename_ids.keys())
    edges, seen = [], set()
    def add_edge(src, dst, kind):
        if src == dst:
            return
        key = (src, dst, kind)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": src, "target": dst, "kind": kind})

    # owns: agent -> its files (exact)
    for f in files:
        add_edge("agent:" + f["owner"], path_id[f["path"]], "owns")

    # content-derived edges (real cross-references between files, and file->agent mentions)
    for f in files:
        fid = path_id[f["path"]]
        content = read_text_bounded(f["path"])
        if not content:
            continue
        low = content.lower()
        refs = 0
        for bn in basenames:
            if refs >= 6 or len(edges) > 700:
                break
            if bn == f["name"].lower():
                continue
            if bn in low:
                for tgt in basename_ids[bn]:
                    if tgt != fid:
                        add_edge(fid, tgt, "refs"); refs += 1
        ment = 0
        for aid, toks in agent_tokens.items():
            if ment >= 3:
                break
            if aid == f["owner"]:
                continue
            if any(t in low for t in toks):
                add_edge(fid, "agent:" + aid, "mentions"); ment += 1

    # memory layer (Obsidian vault) — multicolored by zone, mapped by index.md
    mem = build_memory()
    mem_ids = set()
    for mn in mem["nodes"]:
        nid = mn["id"]
        mem_ids.add(nid)
        nodes.append({"id": nid, "type": "memory", "zone": mn["zone"], "index": mn["index"],
                      "label": mn["title"] or mn["label"], "path": mn["path"],
                      "mtime": mn["mtime"], "size": mn["size"], "preview": mn["preview"],
                      "rel": mn["rel"]})
    for e in mem["edges"]:
        if e["source"] in mem_ids and e["target"] in mem_ids:
            add_edge(e["source"], e["target"], e["kind"])

    # ---- full-brain layer: Hermes profiles (sessions / skills / memories) ----
    try:
        brain = profile_brain()
    except Exception as e:
        print("[graph] profile_brain failed:", e)
        brain = {"profiles": [], "sessions": [], "skills": [], "pmem": []}
    for p in brain["profiles"]:
        pid = p["id"]
        nodes.append({
            "id": "profile:" + pid, "type": "profile",
            "label": _humanize_profile(pid), "profile": pid,
            "session_count": p["session_count"], "message_count": p["message_count"],
            "skill_count": p["skill_count"], "memory_count": p["memory_count"],
            "last_ts": p["last_ts"], "color": "#ADAAB9",
        })
    for s in brain["sessions"]:
        nodes.append({
            "id": "conv:" + s["profile"] + ":" + s["session_id"],
            "type": "conversation", "label": s["title"][:40],
            "profile": s["profile"], "session_id": s["session_id"],
            "model": s["model"], "message_count": s["message_count"],
            "last_ts": s["last_ts"], "source": s["source"], "chat_type": s["chat_type"],
            "preview": s["preview"], "color": "#8E9AB2",
        })
    for sk in brain["skills"]:
        nodes.append({
            "id": "skill:" + sk["profile"] + ":" + sk["name"],
            "type": "skill", "label": sk["name"], "profile": sk["profile"],
            "category": sk["category"], "path": sk["path"], "mtime": sk["mtime"],
            "desc": sk["desc"], "color": "#CDA526",
        })
    for m in brain["pmem"]:
        nm = m["name"].split(".")[0]  # MEMORY.md -> MEMORY
        nodes.append({
            "id": "pmem:" + m["profile"] + ":" + nm,
            "type": "memory", "zone": "profile",
            "label": _humanize_profile(m["profile"]) + " · " + nm,
            "profile": m["profile"], "name": m["name"], "path": m["path"],
            "mtime": m["mtime"], "size": m["size"], "color": "#C6B3BB",
        })
    # owns: profile -> its conversations / skills / memories
    for p in brain["profiles"]:
        pidn = "profile:" + p["id"]
        for s in brain["sessions"]:
            if s["profile"] == p["id"]:
                add_edge(pidn, "conv:" + p["id"] + ":" + s["session_id"], "owns")
        for sk in brain["skills"]:
            if sk["profile"] == p["id"]:
                add_edge(pidn, "skill:" + p["id"] + ":" + sk["name"], "owns")
        for m in brain["pmem"]:
            if m["profile"] == p["id"]:
                add_edge(pidn, "pmem:" + p["id"] + ":" + m["name"].split(".")[0], "owns")

    graph = {"nodes": nodes, "edges": edges}
    _GRAPH_CACHE["t"] = now
    _GRAPH_CACHE["data"] = graph
    return graph

# ---- build full state ----
def build_state():
    files, recent = scan_files()
    agents = parse_agents()
    mem = build_memory()
    rel = probe_relay()
    # activity -> ownership counts + last action
    act = {}
    for e in recent[:40]:
        a = e["owner"]
        act.setdefault(a, {"files": [], "count": 0})
        act[a]["count"] += 1
        if len(act[a]["files"]) < 3:
            act[a]["files"].append({"name": e["name"], "dir": e["dir"], "ago": time_ago(e["mtime"])})
    mem_ts = [m["mtime"] for m in mem["nodes"]] or [0]
    file_ts = [f["mtime"] for f in files] or [0]
    return {
        "agents": agents,
        "files": [{"name": f["name"], "dir": f["dir"], "ext": f["ext"], "size": f["size"], "mtime": f["mtime"], "owner": f["owner"], "path": f["path"]} for f in files[:400]],
        "activity": act,
        "recent": [{"name": e["name"], "dir": e["dir"], "owner": e["owner"], "ago": time_ago(e["mtime"])} for e in recent[:40]],
        "cron": CRON_JOBS,
        "calendar": calendar_events(),
        "relay": rel,
        "memory": {"zones": mem["zones"], "brief": mem["brief"], "total": mem["total"],
                   "velocity": mem["velocity"], "root": mem["root"]},
        "directives": build_directives(),
        "vitals": {
            "agents": len(agents),
            "files": len(files),
            "memory": mem["total"],
            "wiki": mem["zones"].get("wiki", {}).get("count", 0),
            "raw": mem["zones"].get("raw", {}).get("count", 0),
            "outputs": mem["zones"].get("outputs", {}).get("count", 0),
            "runs": mem["zones"].get("runs", {}).get("count", 0),
            "cron_on": sum(1 for c in CRON_JOBS if c.get("on")),
            "relay_vps": rel.get("vps", False),
            "platform": "windows" if IS_WINDOWS else "linux",
            "uptime_s": int(time.time() - _START),
            "velocity_day": mem["velocity"]["day"],
            "velocity_week": mem["velocity"]["week"],
            "last_update": max(file_ts + mem_ts),
        },
        "graph": build_graph(files, agents),
        "platform": "windows" if IS_WINDOWS else "linux",
        "now": datetime.now().isoformat(timespec="seconds"),
    }

def time_ago(ts):
    s = int(time.time() - ts)
    if s < 60: return "just now"
    if s < 3600: return f"{s//60}m ago"
    if s < 86400: return f"{s//3600}h ago"
    return f"{s//86400}d ago"

# ---- chat proxy to the real relay ----
def relay_chat(agent, message, history):
    body = json.dumps({"agent": agent, "message": message, "history": history or []}).encode()
    last_err = None
    for base in RELAY_CANDIDATES:
        try:
            req = urllib.request.Request(base + "/chat", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "Atrium-CC/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode())
                return d.get("reply", ""), d.get("agent", agent)
        except Exception as e:
            last_err = str(e)
    return None, last_err

# ---- tts proxy to the real relay ----
def relay_tts(agent, text):
    body = json.dumps({"agent": agent, "text": text}).encode()
    for base in RELAY_CANDIDATES:
        try:
            req = urllib.request.Request(base + "/tts", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "Atrium-CC/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            continue
    return None

# ---- task proxy to the real relay (/task -> dispatch sidecar) ----
def relay_task(agent, prompt):
    body = json.dumps({"agent": agent, "prompt": prompt}).encode()
    for base in RELAY_CANDIDATES:
        try:
            req = urllib.request.Request(base + "/task", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "Atrium-CC/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            continue
    return {"error": "relay unreachable"}

def relay_task_status(job_id, agent):
    url = "/task/" + job_id + "?agent=" + urllib.parse.quote(agent)
    for base in RELAY_CANDIDATES:
        try:
            req = urllib.request.Request(base + url,
                                         headers={"User-Agent": "Atrium-CC/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            continue
    return {"status": "error", "error": "relay unreachable"}

# ---- HTTP handler ----
class Handler(BaseHTTPRequestHandler):
    server_version = "AtriumCC/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path, ctype):
        try:
            data = open(path, "rb").read()
        except OSError:
            self._json(404, {"error": "not found"}); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/state", "/open", "/read", "/search", "/conv", "/asset") and not _auth_ok(self):
            self._json(401, {"error": "unauthorized"}); return
        if path == "/state":
            self._json(200, build_state()); return
        if path == "/conv":
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            d = read_conversation(qs.get("profile", [""])[0], qs.get("session", [""])[0])
            if d is None:
                self._json(400, {"error": "bad params"}); return
            self._json(200, d); return
        if path == "/read":
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            r = read_preview(qs.get("path", [""])[0])
            if r is None:
                self._json(400, {"error": "path not allowed"}); return
            self._json(200, r); return
        if path == "/search":
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            q = qs.get("q", [""])[0]
            self._json(200, search_vault(q)); return
        if path == "/asset":
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            p = qs.get("path", [""])[0]
            allowed = SCAN_DIRS + [ROOT, VAULT]
            if HERMES_PROFILES:
                allowed += [HERMES_PROFILES]
            if HERMES_SHARED_SKILLS:
                allowed += [HERMES_SHARED_SKILLS]
            if _secret_blocked(p):
                self._json(403, {"error": "blocked filename", "path": p}); return
            ap = _safe_resolve(p, allowed)
            if ap is None:
                self._json(400, {"error": "path not allowed", "path": p}); return
            if _secret_blocked(ap):
                self._json(403, {"error": "blocked filename", "path": p}); return
            if not os.path.isfile(ap):
                self._json(404, {"error": "not found", "path": p}); return
            ext = os.path.splitext(ap)[1].lower()
            ctype = "application/octet-stream"
            if ext in (".html", ".htm"): ctype = "text/html; charset=utf-8"
            elif ext in (".md", ".txt", ".py", ".js", ".css", ".yaml", ".yml", ".log", ".sh"): ctype = "text/plain; charset=utf-8"
            elif ext == ".json": ctype = "application/json"
            elif ext == ".png": ctype = "image/png"
            elif ext in (".jpg", ".jpeg"): ctype = "image/jpeg"
            elif ext == ".webp": ctype = "image/webp"
            elif ext == ".gif": ctype = "image/gif"
            elif ext == ".svg": ctype = "image/svg+xml"
            elif ext == ".pdf": ctype = "application/pdf"
            self._send_file(ap, ctype); return
        if path == "/open":
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            p = qs.get("path", [""])[0]
            self._open_file(p); return
        if path == "/" or path == "/index.html":
            self._send_file(os.path.join(ROOT, "index.html"), "text/html; charset=utf-8"); return
        if path.startswith("/assets/"):
            p = os.path.join(ROOT, path.lstrip("/"))
            if os.path.isfile(p):
                ct = "image/png" if p.endswith(".png") else "application/octet-stream"
                self._send_file(p, ct); return
        if path.startswith("/task/"):
            if not _auth_ok(self):
                self._json(401, {"error": "unauthorized"}); return
            jid = path[len("/task/"):]
            qs = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            agent = qs.get("agent", [""])[0]
            self._json(200, relay_task_status(jid, agent)); return
        self._json(404, {"error": "not found"})

    def _open_file(self, p):
        allowed = SCAN_DIRS + [ROOT, VAULT]
        if HERMES_PROFILES:
            allowed += [HERMES_PROFILES]
        if HERMES_SHARED_SKILLS:
            allowed += [HERMES_SHARED_SKILLS]
        if _secret_blocked(p):
            self._json(403, {"error": "blocked filename", "path": p}); return
        ap = _safe_resolve(p, allowed)
        if ap is None:
            self._json(400, {"error": "path not allowed", "path": p}); return
        if _secret_blocked(ap):
            self._json(403, {"error": "blocked filename", "path": p}); return
        if not os.path.isfile(ap):
            self._json(404, {"error": "not found", "path": p}); return
        if IS_WINDOWS:
            try:
                os.startfile(ap)  # noqa — intentional local open (Vincent's rule)
                self._json(200, {"ok": True, "opened": ap})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        # Linux (VPS): serve the file content for view/download
        try:
            data = open(ap, "rb").read()
        except OSError:
            self._json(404, {"error": "unreadable"}); return
        if len(data) > 5_000_000:
            data = data[:5_000_000]
        ext = os.path.splitext(ap)[1].lower()
        ctype = "application/octet-stream"
        if ext in (".html", ".htm"): ctype = "text/html; charset=utf-8"
        elif ext in (".md", ".txt", ".py", ".js", ".css", ".yaml", ".yml", ".log", ".sh"): ctype = "text/plain; charset=utf-8"
        elif ext == ".json": ctype = "application/json"
        elif ext == ".png": ctype = "image/png"
        elif ext in (".jpg", ".jpeg"): ctype = "image/jpeg"
        elif ext == ".pdf": ctype = "application/pdf"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/auth":
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                d = json.loads(self.rfile.read(n).decode())
            except Exception:
                self._json(400, {"error": "bad json"}); return
            if hmac.compare_digest((d.get("pin") or "").strip(), CC_TOKEN):
                data = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie",
                    f"{AUTH_COOKIE}={_session_value()}; HttpOnly; SameSite=Lax; Path=/")
                self.send_header("Content-Length", str(len(data)))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json(401, {"error": "invalid pin"})
            return
        if path in ("/chat", "/tts", "/task") and not _auth_ok(self):
            self._json(401, {"error": "unauthorized"}); return
        if path == "/chat":
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                d = json.loads(self.rfile.read(n).decode())
            except Exception:
                self._json(400, {"error": "bad json"}); return
            reply, err = relay_chat(d.get("agent", "reception"), d.get("message", ""), d.get("history"))
            if reply is None:
                self._json(502, {"error": "relay unreachable", "detail": err}); return
            self._json(200, {"reply": reply, "agent": d.get("agent")}); return
        if path == "/tts":
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                d = json.loads(self.rfile.read(n).decode())
            except Exception:
                self._json(400, {"error": "bad json"}); return
            audio = relay_tts(d.get("agent", "reception"), d.get("text", ""))
            if audio is None:
                self._json(502, {"error": "tts unreachable"}); return
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(audio)))
            self._cors()
            self.end_headers()
            self.wfile.write(audio)
            return
        if path == "/task":
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                d = json.loads(self.rfile.read(n).decode())
            except Exception:
                self._json(400, {"error": "bad json"}); return
            res = relay_task(d.get("agent", "thabo"), (d.get("prompt") or "").strip())
            if not res or res.get("error"):
                self._json(502, res or {"error": "relay unreachable"}); return
            self._json(200, res); return
        self._json(404, {"error": "not found"})

    def log_message(self, *a):
        pass  # quiet

import urllib.parse  # noqa (used in do_GET)

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8800
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Atrium Command Center backend on http://localhost:{port}")
    print(f"  /state  -> real data   |  /chat -> live relay proxy")
    srv.serve_forever()

if __name__ == "__main__":
    main()
