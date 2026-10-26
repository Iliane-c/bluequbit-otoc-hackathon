"""G4: same test on qubit 0 with the coarser threshold 1e-4 (1e-5 was too slow).

Gives up after 10 minutes.
Originally: test_g4_1e4.py
"""

import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 38
z = "I" * (N - 1) + "Z"  # Z on qubit 0

print("G4 qubit 0, pauli-path threshold 1e-4...")
try:
    job = bq.run("Duke_G4_0", device="pauli-path", pauli_sum=[(z, 1.0)],
                 options={"pauli_path_truncation_threshold": 1e-4}, asynchronous=True)
    print(f"Submitted (job {job.job_id})")

    t0 = time.time()
    while True:
        time.sleep(5)
        result = bq.get(job.job_id)
        if result.run_status == "COMPLETED":
            print(f"Qubit 0 = {result.expectation_value} ({result.run_time_ms / 1000:.1f}s)")
            break
        if result.run_status not in ("RUNNING", "PENDING", "QUEUED"):
            print(f"Job failed: {result.run_status}")
            break
        if time.time() - t0 > 10 * 60:
            print("Too slow.")
            break
except Exception as e:
    print("Run with threshold 1e-4 failed:", e)
