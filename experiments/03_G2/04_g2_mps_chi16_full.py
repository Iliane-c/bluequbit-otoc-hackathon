"""G2: final sweep with MPS chi=16 (the submitted G2 result).

chi=16 was the best accuracy/cost trade-off found with g2_single_job_cost.py.
Originally: run_g2_chi16_full.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

n = 36
problem = "G2"
all_ids = [f"Duke_{problem}_{q}" for q in range(n)]
CAP = 2.0  # total budget in $
spent = 0.0
vals = np.full(n, np.nan)

print(f"{problem} sweep ({n} qubits), mps.cpu chi=16...")

for q in range(n):
    if spent >= CAP:
        print("Budget cap reached, stopping.")
        break

    z = "I" * (n - 1 - q) + "Z" + "I" * q
    cid = all_ids[q]
    try:
        job = bq.run(cid, device="mps.cpu", pauli_sum=[(z, 1.0)],
                     options={"mps_bond_dimension": 16}, timeout=120)
        cost = getattr(job, "cost", 0.0) or 0.0
        spent += cost
        vals[q] = job.expectation_value
        print(f"[{q + 1}/{n}] {cid} -> {vals[q]:.6f} | cost ${cost:.4f} | total ${spent:.4f}")
    except Exception as e:
        print(f"Error on {cid}: {e}")

ok = ~np.isnan(vals)
print(f"\nComputed qubits: {ok.sum()}/{n}")

if ok.sum() == n and np.nanstd(vals) > 1e-6:
    with open(f"{problem}.csv", "w", newline="") as f:
        csv.writer(f).writerows([(all_ids[q], float(vals[q])) for q in range(n)])
    print(f"{problem}.csv written with chi=16 values.")
else:
    print(f"{problem}.csv not written: missing values or all values identical.")
