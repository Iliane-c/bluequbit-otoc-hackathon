"""G4: complete baseline with MPS chi=32, 3 jobs in parallel (thread pool).

Gives a full, submittable G4_chi32.csv quickly. Jobs that hit the hackathon
limit of 5 parallel jobs are retried after 15 seconds. If at most 2 qubits are
still missing at the end, they are filled with the mean value.
Originally: run_g4_parallel_chi32.py
"""

import concurrent.futures
import csv
import time

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 38
CHI = 32
MAX_WORKERS = 3  # below the platform limit of 5 concurrent jobs
MAX_RETRIES = 3


def zstr(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


def compute_qubit(q):
    """Run one qubit (blocking) with retries; return (qubit, value, cost)."""
    cid = f"Duke_G4_{q}"
    for attempt in range(MAX_RETRIES):
        t0 = time.time()
        try:
            job = bq.run(cid, device="mps.cpu", pauli_sum=[(zstr(q), 1.0)],
                         options={"mps_bond_dimension": CHI}, timeout=600)
            value = job.expectation_value
            cost = getattr(job, "cost", 0.0) or 0.0
            print(f"[chi={CHI}] qubit {q} | {value:.5f} | ${cost:.4f} | {time.time() - t0:.1f}s")
            return q, value, cost
        except Exception as e:
            message = str(e)
            if "HACKATHON_PARALLEL_JOBS_LIMIT" in message:
                print(f"[chi={CHI}] qubit {q} hit the parallel limit "
                      f"(attempt {attempt + 1}/{MAX_RETRIES}), retrying in 15s")
                time.sleep(15)
            else:
                print(f"[chi={CHI}] qubit {q} failed: {message[:150]}")
                time.sleep(5)
    return q, np.nan, 0.0


print(f"G4 sweep, mps.cpu chi={CHI}, {MAX_WORKERS} workers...")
vals = np.full(N, np.nan)
total_cost = 0.0
t_start = time.time()

with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(compute_qubit, q) for q in range(N)]
    for future in concurrent.futures.as_completed(futures):
        q, value, cost = future.result()
        vals[q] = value
        total_cost += cost

print(f"Done in {time.time() - t_start:.1f}s, total cost ${total_cost:.3f}")

if not np.isnan(vals).any():
    with open("G4_chi32.csv", "w", newline="") as f:
        csv.writer(f).writerows([(f"Duke_G4_{q}", float(vals[q])) for q in range(N)])
    print("G4_chi32.csv written.")
else:
    missing = [q for q in range(N) if np.isnan(vals[q])]
    print(f"Missing qubits: {missing}")
    if len(missing) <= 2 and not np.isnan(vals).all():
        vals[missing] = np.nanmean(vals)  # mean imputation for a couple of gaps
        with open("G4_chi32.csv", "w", newline="") as f:
            csv.writer(f).writerows([(f"Duke_G4_{q}", float(vals[q])) for q in range(N)])
        print("G4_chi32.csv written, missing qubits filled with the mean.")
