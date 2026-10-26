"""G3: MPS sweep at chi=64 with a cost guard on every job.

Each job is submitted asynchronously so its estimated cost can be read before
it runs; it is cancelled if the estimate exceeds $0.50 or the $5 global cap.
Originally: run_g3_mps_protected.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

n = 36
CHI = 64
CAP = 5.0  # global cap in $
EST_MAX = 0.5  # max estimated cost per job in $
spent = 0.0
vals = np.full(n, np.nan)

print(f"G3 sweep with cost guard, mps.cpu chi={CHI}...")

for q in range(n):
    z = "I" * (n - 1 - q) + "Z" + "I" * q
    cid = f"Duke_G3_{q}"

    job = bq.run(cid, device="mps.cpu", pauli_sum=[(z, 1.0)],
                 options={"mps_bond_dimension": CHI}, asynchronous=True)

    # Cancel before it costs anything if the estimate is too high
    est_cost = getattr(job, "estimated_cost", 0.0) or 0.0
    if est_cost > EST_MAX or spent + est_cost > CAP:
        bq.cancel(job.job_id)
        print(f"Stop: cost limit reached at qubit {q} (estimate ${est_cost:.2f})")
        break

    try:
        result = bq.wait(job.job_id, timeout=600)
    except Exception as e:
        bq.cancel(job.job_id)
        print(f"Timeout on {cid}, job cancelled: {e}")
        break

    if not result.ok:
        print(f"Error on {cid}: {getattr(result, 'error_message', 'unknown')}")
        break

    cost = getattr(result, "cost", 0.0) or 0.0
    spent += cost
    vals[q] = result.expectation_value
    print(f"[{q + 1}/{n}] {cid} | {vals[q]:.6f} | ${cost:.4f} | total ${spent:.4f}", flush=True)

if not np.isnan(vals).any():
    with open("G3.csv", "w", newline="") as f:
        csv.writer(f).writerows([(f"Duke_G3_{q}", float(vals[q])) for q in range(n)])
    print("\nG3.csv written.")
else:
    print("\nIncomplete sweep, G3.csv not written.")
