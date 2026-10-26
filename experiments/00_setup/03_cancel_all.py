"""Cancel every pending or running job (one search per status).

Written after a run left paid jobs running in the background.
Originally: cancel_all.py
"""

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

print("Checking for active or pending jobs...")
found = False
for status in ("RUNNING", "PENDING", "QUEUED"):
    for job in bq.search(run_status=status):
        found = True
        est_cost = getattr(job, "estimated_cost", 0.0) or 0.0
        print(f"Cancelling job {job.job_id} | Device: {job.device} | Status: {status} | "
              f"Est. cost: ${est_cost:.2f}")
        bq.cancel(job.job_id)

if not found:
    print("No active or pending jobs found.")
else:
    print("All stray jobs cancelled.")
