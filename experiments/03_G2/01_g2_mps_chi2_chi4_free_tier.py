"""G2 (36 qubits, 1D chain): first MPS attempt, restricted to free jobs.

Strategy: two full passes with very small bond dimensions (chi=2, then chi=4),
checking each job's estimated cost first and skipping anything that is not free.
The corr^2 between the two passes is a cheap convergence indicator.
Originally: test_g2.py
"""

import csv

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

# Cost guards (0.0 = free jobs only)
CAP_JOB = 0.0
CAP_TOTAL = 2.0
spent = 0.0

n = 36
problem = "G2"
all_ids = [f"Duke_{problem}_{q}" for q in range(n)]


def zstr(n, q):
    """Pauli string with Z on qubit q (little-endian)."""
    return "I" * (n - 1 - q) + "Z" + "I" * q


def safe_run(cid, n, q, device, options):
    """Run one job only if bq.estimate says it fits the cost caps."""
    global spent
    try:
        est = bq.estimate(cid, device=device)
        cost = est.estimated_cost or 0.0
        if est.error_message or cost > CAP_JOB or spent + cost > CAP_TOTAL:
            print(f"SKIP {cid} on {device}: estimated ${cost} {est.error_message or ''}")
            return np.nan
        job = bq.run(cid, device=device, pauli_sum=[(zstr(n, q), 1.0)],
                     options=options, timeout=600)
        spent += cost
        return job.expectation_value
    except Exception as e:
        print(f"Error on {cid}: {e}")
        return np.nan


def full_pass(device, options):
    """Run every qubit with the given device and options."""
    print(f"\nPass with device={device}, options={options}")
    results = []
    for q in range(n):
        value = safe_run(all_ids[q], n, q, device, options)
        results.append(value)
        if not np.isnan(value):
            print(f"  [{q + 1}/{n}] {all_ids[q]} -> {value:.8f}")
    return np.array(results)


v1 = full_pass("mps.cpu", {"mps_bond_dimension": 2})
v2 = full_pass("mps.cpu", {"mps_bond_dimension": 4})

# Agreement between the two passes
ok = ~np.isnan(v1) & ~np.isnan(v2)
if np.any(ok):
    print(f"\nAgreement chi=2 vs chi=4 (corr^2): {np.corrcoef(v1[ok], v2[ok])[0, 1] ** 2:.6f}")

# Prefer chi=4, fall back to chi=2, then to 1.0
v = np.where(np.isnan(v2), v1, v2)
v = np.where(np.isnan(v), 1.0, v)

with open(f"{problem}.csv", "w", newline="") as f:
    csv.writer(f).writerows([(all_ids[q], float(v[q])) for q in range(n)])

print(f"\n{problem}.csv written for {n} qubits.")
