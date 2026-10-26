"""G3: same chi=32 MPS sweep, with retries.

The previous run hit timeouts and transient API errors, so each job now gets
3 attempts and a 10-minute timeout.
Originally: run_g3_mps_robust.py
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
CAP = 2.0
MAX_RETRIES = 3
spent = 0.0
vals = np.full(n, np.nan)

print(f"{problem} sweep with retries, mps.cpu chi=32...")

for q in range(n):
    if spent >= CAP:
        print("Budget cap of $2.00 reached, stopping.")
        break

    z = "I" * (n - 1 - q) + "Z" + "I" * q
    cid = all_ids[q]
    success = False
    for attempt in range(MAX_RETRIES):
        try:
            job = bq.run(cid, device="mps.cpu", pauli_sum=[(z, 1.0)],
                         options={"mps_bond_dimension": 32}, timeout=600)
            cost = getattr(job, "cost", 0.0) or 0.0
            spent += cost
            vals[q] = job.expectation_value
            print(f"[{q + 1}/{n}] {cid} | {vals[q]:.6f} | ${cost:.4f} | total ${spent:.4f}")
            success = True
            break
        except Exception as e:
            print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed on {cid}: {e}")
            time.sleep(5)

    if not success:
        print(f"Skipping {cid} after {MAX_RETRIES} failed attempts.")

ok = ~np.isnan(vals)
print(f"\nComputed qubits: {ok.sum()}/{n}")

if ok.sum() == n and np.nanstd(vals) > 1e-6:
    with open(f"{problem}.csv", "w", newline="") as f:
        csv.writer(f).writerows([(all_ids[q], float(vals[q])) for q in range(n)])
    print(f"{problem}.csv written.")
else:
    print(f"{problem}.csv not written: some values are missing.")
