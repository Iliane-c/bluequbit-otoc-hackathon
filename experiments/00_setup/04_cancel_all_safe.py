"""Safer version of cancel_all.py.

`bq.search(run_status=...)` crashed in the SDK when no job matched, so this
version fetches all jobs once and filters on the status locally.
Originally: cancel_all_safe.py
"""

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

print("Checking for active or pending jobs...")
try:
    jobs = bq.search() or []
    found = False
    for job in jobs:
        status = getattr(job, "run_status", "")
        if status in ("RUNNING", "PENDING", "QUEUED"):
            found = True
            est_cost = getattr(job, "estimated_cost", 0.0) or 0.0
            print(f"Cancelling job {job.job_id} | Device: {job.device} | Status: {status} | "
                  f"Est. cost: ${est_cost:.2f}")
            bq.cancel(job.job_id)
    if not found:
        print("No active or pending jobs found.")
except Exception as e:
    print(f"Job search failed: {e}")
    print("If no jobs are running, it is safe to proceed.")
