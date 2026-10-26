"""S3 (30 qubits, 5x6 grid): exact CPU simulation by ID.

30 qubits still fit the exact state-vector simulator, so these values serve as
ground truth to validate the local Pauli-propagation code (local_pauli_propagation.py).
Originally: test3.py
"""

import csv

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

circuit = "S3"
n = 30
rows = []

print(f"Running {circuit} ({n} circuits) on the exact CPU simulator...")

for q in range(n):
    cid = f"Duke_{circuit}_{q}"
    z = "I" * (n - 1 - q) + "Z" + "I" * q  # Z on qubit q (little-endian)
    try:
        job = bq.run(cid, device="cpu", pauli_sum=[(z, 1.0)])
        rows.append((cid, job.expectation_value))
        print(f"{cid} -> {job.expectation_value}")
    except Exception as e:
        print(f"Error on {cid}: {e}")

# Submission format: circuit_id,value (no header)
with open(f"{circuit}.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)

print(f"{circuit}.csv written.")
