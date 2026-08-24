#!/bin/bash
# Atrium glass-OS concept batch — 3 parallel z_image jobs (free plan)
cd /c/Users/VincentMamashela/atrium-command-center/design-brief
rm -f gen_status.txt gen_p1.log gen_p2.log gen_p3.log
run_job () {
  local i=$1
  (cat "prompts/p${i}-"*.txt | higgsfield generate create z_image --wait --aspect_ratio 16:9 > "gen_p${i}.log" 2>&1
   echo "job${i} exit=$?" >> gen_status.txt) &
}
run_job 1
run_job 2
run_job 3
wait
echo "ALL DONE"
