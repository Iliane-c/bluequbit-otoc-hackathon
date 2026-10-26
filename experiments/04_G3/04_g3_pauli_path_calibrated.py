"""G3: Pauli-path sweep whose threshold is chosen from a calibration job.

1. Run the butterfly qubit 14 first: it is the most scrambled, hence the most
   expensive job, so 36 x its cost is an upper bound for the full sweep.
2. Pick the threshold from that projection (1e-3, 3e-3 or 1e-2), keeping the
   G3 budget under $15 so credits remain for G4.
3. Sweep the other 35 qubits and export the CSV if all of them succeeded.
Originally: run_g3_pauli_strategy.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 36
BUDGET_G3 = 15.0  # dollars reserved for G3; the rest is kept for G4
spent = 0.0


def run_job(q, threshold):
    """Run qubit q on the pauli-path device and return (value, cost)."""
    global spent
    z = "I" * (N - 1 - q) + "Z" + "I" * q
    job = bq.run(f"Duke_G3_{q}", device="pauli-path", pauli_sum=[(z, 1.0)],
                 options={"pauli_path_truncation_threshold": threshold}, timeout=300)
    cost = getattr(job, "cost", 0.0) or 0.0
    spent += cost
    return job.expectation_value, cost


# Step 1: calibration on the butterfly qubit
print("Step 1: calibration on qubit 14 (butterfly, most expensive job)")
try:
    v14, c14 = run_job(14, 1e-3)
    print(f"qubit 14 -> {v14:.5f} | ${c14:.4f}")
    est_total = 36 * c14
    print(f"Projected upper bound for the sweep: ${est_total:.2f}")
except Exception as e:
    raise SystemExit(f"Calibration failed: {e}")

# Step 2: choose the threshold from the projected cost
if est_total <= 12.0:
    threshold = 1e-3
elif est_total <= 20.0:
    threshold = 3e-3
else:
    threshold = 1e-2
print(f"Chosen threshold: {threshold}")

# Step 3: sweep the remaining qubits
vals = np.full(N, np.nan)
vals[14] = v14
print(f"\nStep 2: sweep of all qubits at threshold {threshold}")

for q in range(N):
    if q == 14:
        continue  # already computed
    if spent >= BUDGET_G3:
        print(f"Budget of ${BUDGET_G3:.2f} reached, stopping to keep credits for G4.")
        break
    try:
        value, cost = run_job(q, threshold)
        vals[q] = value
        print(f"[{q + 1}/{N}] Duke_G3_{q} | {value:.5f} | ${cost:.4f} | total ${spent:.4f}")
    except Exception as e:
        print(f"Error on Duke_G3_{q}: {e}")

if not np.isnan(vals).any():
    filename = f"G3_{threshold:g}.csv"
    with open(filename, "w", newline="") as f:
        csv.writer(f).writerows([(f"Duke_G3_{q}", float(vals[q])) for q in range(N)])
    print(f"\n{filename} written.")
else:
    print("\nIncomplete sweep, CSV not written.")

print(f"Total spent on G3: ${spent:.4f}")
