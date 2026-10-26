"""G4: can Pauli path handle the butterfly qubit? Test on qubit 0 at threshold 1e-5.

Qubit 0 is the butterfly (the hardest job). Polls every 10 s and gives up
after 15 minutes.
Originally: test_g4_q0.py
"""

import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 38  # qubits 0 to 37
z = "I" * (N - 1) + "Z"  # Z on qubit 0

print("G4 qubit 0, pauli-path threshold 1e-5...")
t0 = time.time()
job = bq.run("Duke_G4_0", device="pauli-path", pauli_sum=[(z, 1.0)],
             options={"pauli_path_truncation_threshold": 1e-5}, asynchronous=True)
print(f"Submitted (job {job.job_id}), waiting...")

while True:
    time.sleep(10)
    result = bq.get(job.job_id)
    if result.run_status == "COMPLETED":
        print(f"Qubit 0 = {result.expectation_value} ({result.run_time_ms / 1000:.1f}s)")
        break
    if result.run_status not in ("RUNNING", "PENDING", "QUEUED"):
        print(f"Job failed: {result.run_status}")
        break
    if time.time() - t0 > 15 * 60:
        print("Too slow, giving up.")
        bq.cancel(job.job_id)
        break
