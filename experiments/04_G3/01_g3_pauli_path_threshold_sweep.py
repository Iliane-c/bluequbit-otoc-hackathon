"""G3 (36 qubits, 6x6 Clifford grid): first Pauli-path attempt.

G3 is mostly Clifford gates, which map a Pauli string to a single Pauli string,
so Pauli-path propagation should work well. Plan: a full pass at threshold 1e-3,
then 1e-4, comparing the two passes (corr^2) to judge convergence, with a $3 cap.
Originally: run_g3_full.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()


def zstr(n, q):
    """Pauli string with Z on qubit q (little-endian)."""
    return "I" * (n - 1 - q) + "Z" + "I" * q


def run_job(cid, n, q, threshold):
    job = bq.run(cid, device="pauli-path", pauli_sum=[(zstr(n, q), 1.0)],
                 options={"pauli_path_truncation_threshold": threshold}, timeout=300)
    return job.expectation_value, (getattr(job, "cost", 0.0) or 0.0), getattr(job, "run_time_ms", 0)


n = 36
problem = "G3"
all_ids = [f"Duke_{problem}_{q}" for q in range(n)]
CAP = 3.0
spent = 0.0
prev = None

print(f"Pauli-path threshold sweep for {problem}...")

for threshold in (1e-3, 1e-4):
    print(f"\n--- threshold {threshold} ---")
    vals = np.full(n, np.nan)

    for q in range(n):
        if spent >= CAP:
            print("Budget cap of $3.00 reached, stopping.")
            break
        try:
            value, cost, ms = run_job(all_ids[q], n, q, threshold)
            spent += cost
            vals[q] = value
            print(f"[{q + 1}/{n}] {all_ids[q]} | {value:.5f} | ${cost:.4f} | "
                  f"total ${spent:.4f} | {ms} ms")
        except Exception as e:
            print(f"Error on {all_ids[q]} at threshold {threshold}: {e}")

    if np.isnan(vals).any():
        print("Incomplete pass, stopping.")
        break

    filename = f"{problem}_{threshold:g}.csv"
    with open(filename, "w", newline="") as f:
        csv.writer(f).writerows([(all_ids[q], float(vals[q])) for q in range(n)])
    print(f"Saved {filename}")

    if prev is not None:
        r2 = np.corrcoef(prev, vals)[0, 1] ** 2
        print(f"Convergence (corr^2 with previous threshold): {r2:.6f}")
        if r2 > 0.99:
            print("Converged: further refinement is probably unnecessary.")
    prev = vals

print(f"\nDone. Total spent: ${spent:.4f}")
