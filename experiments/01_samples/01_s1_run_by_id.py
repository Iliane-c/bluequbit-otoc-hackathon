"""S1 (4 qubits): first end-to-end run, by ID, with the exact CPU simulator.

This is the reference snippet from the challenge page. It produced the first
submission (S1.csv).
Originally: test_1.py
"""

import csv

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()  # reads BLUEQUBIT_API_TOKEN

circuit = "S1"
n = bq.get_circuit_info(f"Duke_{circuit}_0").num_qubits  # free call
rows = []
for q in range(n):
    cid = f"Duke_{circuit}_{q}"
    # Z on qubit q; BlueQubit is little-endian, so qubit 0 is the rightmost character
    z = "I" * (n - 1 - q) + "Z" + "I" * q
    job = bq.run(cid, device="cpu", pauli_sum=[(z, 1.0)])
    rows.append((cid, job.expectation_value))
    print(cid, job.expectation_value)

with open(f"{circuit}.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)
