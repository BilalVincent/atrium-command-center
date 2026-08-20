#!/usr/bin/env python3
"""Atrium task dispatch sidecar — runs one-shot Hermes tasks on worker profiles.

Runs as a compose service alongside hermes-agent (shares the same image, so the
`hermes` CLI is available). Listens on 0.0.0.0:DISPATCH_PORT (default 8899) so
the relay reaches it via the compose network (http://dispatch:8899).

Persona routing: the front charters (amara/thabo/liam/naledi/marcus/duo) map to
backend worker profiles. Each stays in its lane; the worker's own soul + skills
do the heavy lifting.

Async:
  POST /task      {agent?, worker?, prompt, image?, toolsets?} -> {job_id, worker, status}
  GET  /task/<id> -> {status, result?, error?, worker?}
  GET  /health    -> {ok, jobs}
"""
import json, subprocess, threading, time, uuid, os, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERMES = "/opt/hermes/.venv/bin/hermes"
PORT = int(os.environ.get("DISPATCH_PORT", "8899"))
MAX_TURNS = int(os.environ.get("DISPATCH_MAX_TURNS", "12"))

# persona -> backend worker profile (front charter -> specialist)
PERSONA_WORKER = {
    "amara":     "writer-agent",
    "thabo":     "ops-agent",
    "liam":      "writer-agent",
    "naledi":    "writer-agent",
    "marcus":    "codi-agent",
    "duo":       "codi-agent",
    "reception": "ops-agent",
}

# worker -> default toolsets (capability granted to that worker for the task)
WORKER_TOOLSETS = {
    "ops-agent":    "web",
    "writer-agent": "web,file",
    "codi-agent":   "web,terminal,file",
    "choppy-agent": "file",
    "scribe-agent": "file",
    "james-agent":  "web,file",
}

# worker -> deliverable bar (appended to the prompt; enforces quality)
WORKER_CRAFT = {
    "ops-agent":    (" Deliver a structured brief. You MUST actually run web_search / "
                     "web_extract and paste the EXACT URLs you retrieved inline. Every factual "
                     "claim needs a real URL next to it. If you cannot retrieve a real URL for "
                     "a claim, DELETE the claim instead of guessing. Never write placeholder "
                     "brackets like '[citation needed]' or '[source]' — only real URLs. "
                     "Never invent company names, figures, or sources."),
    "writer-agent": (" Deliver clean, ready-to-use prose. Do not invent facts; flag "
                     "anything you need confirmed before writing."),
    "codi-agent":   (" Deliver real, runnable code with a short explanation. Do not "
                     "fabricate test results, API responses, or benchmark numbers."),
}

JOBS = {}
_RUN_LOCK = threading.Lock()      # serialize hermes spawns (one runtime at a time)
_JOBS_LOCK = threading.Lock()


def _strip(out):
    out = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", out)
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    return "\n".join(l for l in out.splitlines()
                     if l.strip() and not l.startswith("session_id:"))


def _run(job_id, worker, prompt, image, toolsets):
    with _JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["started"] = time.time()
    with _RUN_LOCK:
        cmd = [HERMES, "-p", worker, "chat", "-q", prompt, "-Q", "--yolo",
               "--max-turns", str(MAX_TURNS), "-t", toolsets]
        if image:
            cmd += ["--image", image]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                               cwd="/opt/data")
            out = _strip(p.stdout or "")
            err = (p.stderr or "").strip()
            with _JOBS_LOCK:
                if out:
                    JOBS[job_id]["status"] = "done"
                    JOBS[job_id]["result"] = out
                else:
                    JOBS[job_id]["status"] = "error"
                    JOBS[job_id]["error"] = err[-1500:] or "no output"
        except subprocess.TimeoutExpired:
            with _JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = "timeout (15m)"
        except Exception as e:
            with _JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = str(e)


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        d = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n).decode()) if n else {}

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "jobs": len(JOBS)})
            return
        if self.path.startswith("/task/"):
            jid = self.path.split("/")[-1]
            with _JOBS_LOCK:
                j = JOBS.get(jid)
            if not j:
                self._json(404, {"error": "unknown job"})
                return
            self._json(200, j)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/task":
            try:
                d = self._body()
            except Exception:
                self._json(400, {"error": "bad json"}); return
            prompt = (d.get("prompt") or "").strip()
            if not prompt:
                self._json(400, {"error": "missing prompt"}); return
            worker = d.get("worker") or PERSONA_WORKER.get(
                str(d.get("agent", "")).lower(), "ops-agent")
            toolsets = d.get("toolsets") or WORKER_TOOLSETS.get(worker, "web")
            image = d.get("image")
            prompt += WORKER_CRAFT.get(worker, "")
            jid = uuid.uuid4().hex[:12]
            with _JOBS_LOCK:
                JOBS[jid] = {"status": "queued", "worker": worker,
                             "created": time.time(), "result": ""}
            threading.Thread(target=_run,
                             args=(jid, worker, prompt, image, toolsets),
                             daemon=True).start()
            self._json(200, {"job_id": jid, "status": "queued", "worker": worker})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
