"""G3: chi=32 MPS sweep without a budget cap (chi=32 jobs on mps.cpu were free).

Same as the retry version, but stops at the first qubit that fails 3 times so
that a broken run is noticed immediately.
Originally: run_g3_mps_free.py
"""

import csv
import time

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

n = 36
problem = "G3"
all_ids = [f"Duke_{problem}_{q}" for q in range(n)]
BOND_DIM = 32
MAX_RETRIES = 3
spent = 0.0
vals = np.full(n, np.nan)

print(f"{problem} sweep, mps.cpu chi={BOND_DIM}...")

for q in range(n):
    z = "I" * (n - 1 - q) + "Z" + "I" * q
    cid = all_ids[q]
    success = False
    for attempt in range(MAX_RETRIES):
        try:
            job = bq.run(cid, device="mps.cpu", pauli_sum=[(z, 1.0)],
                         options={"mps_bond_dimension": BOND_DIM}, timeout=600)
            cost = getattr(job, "cost", 0.0) or 0.0
            spent += cost
            vals[q] = job.expectation_value
            print(f"[{q + 1}/{n}] {cid} | {vals[q]:.6f} | ${cost:.4f} | total ${spent:.4f}",
                  flush=True)
            success = True
            break
        except Exception as e:
            print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed on {cid}: {e}")
            time.sleep(5)

    if not success:
        print(f"Stopping: {cid} failed {MAX_RETRIES} times.")
        break

ok = ~np.isnan(vals)
print(f"\nComputed qubits: {ok.sum()}/{n}")

if ok.sum() == n:
    with open(f"{problem}.csv", "w", newline="") as f:
        csv.writer(f).writerows([(all_ids[q], float(vals[q])) for q in range(n)])
    print(f"{problem}.csv written.")
else:
    print(f"{problem}.csv not written: some values are missing.")
