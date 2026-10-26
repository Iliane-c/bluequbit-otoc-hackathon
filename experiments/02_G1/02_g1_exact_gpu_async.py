"""G1: exact state-vector simulation on GPU, all 30 jobs submitted asynchronously.

Submitting everything first and then waiting is much faster than running the
jobs one by one. Two qubits (4 and 23) failed in this run; see g1_fill_missing.py.
Originally: test_g1_async.py
"""

import csv

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

n = 30
problem = "G1"
ids = [f"Duke_{problem}_{q}" for q in range(n)]
jobs = {}

# Step 1: submit all jobs without waiting
print(f"Submitting {n} jobs to the GPU backend...")
for q in range(n):
    z = "I" * (n - 1 - q) + "Z" + "I" * q  # Z on qubit q (little-endian)
    try:
        job = bq.run(ids[q], device="gpu", pauli_sum=[(z, 1.0)],
                     asynchronous=True, job_name=f"G1_{q}")
        jobs[q] = job
        print(f"  submitted {ids[q]} (job {job.job_id})")
    except Exception as e:
        print(f"Error submitting {ids[q]}: {e}")

# Step 2: wait for each result
print("\nAll jobs submitted, waiting for results...\n")
rows = []
for q, job in jobs.items():
    try:
        result = bq.wait(job.job_id)
        status = getattr(result, "run_status", "UNKNOWN")
        err = getattr(result, "error_message", None)
        print(f"qubit {q:02d}: status={status} <Z>={result.expectation_value:.8f}"
              + (f" error={err}" if err else ""))
        rows.append((ids[q], result.expectation_value))
    except Exception as e:
        print(f"Error retrieving qubit {q}: {e}")

# Step 3: write the submission (no header)
with open(f"{problem}.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)

print(f"\n{problem}.csv written.")
