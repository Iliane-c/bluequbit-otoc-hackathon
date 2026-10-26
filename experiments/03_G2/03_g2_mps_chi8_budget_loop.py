"""G2: full sweep with MPS chi=8, tracking the real cost of each job against a $1 cap.

Unlike the first attempt, this uses the cost actually billed (job.cost) rather
than the estimate. The CSV is only written if every qubit succeeded and the
values are not all equal (all-equal values score 0).
Originally: test_g2_loop.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

n = 36
CAP = 1.0  # total budget in $
spent = 0.0
vals = np.full(n, np.nan)

print("G2 sweep, mps.cpu chi=8, real-cost tracking...")

for q in range(n):
    if spent >= CAP:
        print("Budget cap reached, stopping.")
        break

    z = "I" * (n - 1 - q) + "Z" + "I" * q
    cid = f"Duke_G2_{q}"
    try:
        job = bq.run(cid, device="mps.cpu", pauli_sum=[(z, 1.0)],
                     options={"mps_bond_dimension": 8}, timeout=120)
        cost = getattr(job, "cost", 0.0) or 0.0
        spent += cost
        vals[q] = job.expectation_value
        print(f"[{q + 1}/{n}] {cid} -> {vals[q]:.6f} | cost ${cost:.4f} | total ${spent:.4f}")
    except Exception as e:
        print(f"Error on {cid}: {e}")

ok = ~np.isnan(vals)
print(f"Computed qubits: {ok.sum()}/{n}")

if ok.sum() == n and np.nanstd(vals) > 1e-6:
    with open("G2.csv", "w", newline="") as f:
        csv.writer(f).writerows([(f"Duke_G2_{q}", float(vals[q])) for q in range(n)])
    print("G2.csv written.")
else:
    print("G2.csv not written: missing values or all values identical.")
