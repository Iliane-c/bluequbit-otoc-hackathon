"""G1: recompute only the qubits missing from G1.csv (4 and 23 failed in the async run).

The submission portal rejects files with missing IDs, so the file is completed
and rewritten in qubit order.
Originally: fix_g1.py
"""

import csv
import os

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

problem = "G1"
n = 30
all_ids = [f"Duke_{problem}_{q}" for q in range(n)]

# Load the values already computed
existing = {}
if os.path.exists(f"{problem}.csv"):
    with open(f"{problem}.csv") as f:
        for row in csv.reader(f):
            if len(row) == 2:
                existing[row[0]] = float(row[1])

print(f"Found {len(existing)}/{n} circuits in {problem}.csv")

missing = [cid for cid in all_ids if cid not in existing]
if not missing:
    print("All circuits are already present.")
else:
    print(f"Computing missing circuits: {missing}")
    for cid in missing:
        q = int(cid.split("_")[-1])
        z = "I" * (n - 1 - q) + "Z" + "I" * q
        print(f"Running {cid} on GPU...")
        try:
            job = bq.run(cid, device="gpu", pauli_sum=[(z, 1.0)])
            existing[cid] = job.expectation_value
            print(f"  {cid} -> {job.expectation_value:.8f}")
        except Exception as e:
            print(f"Error on {cid}: {e}")

    # Rewrite the file sorted by qubit
    rows = [(cid, existing[cid]) for cid in all_ids if cid in existing]
    with open(f"{problem}.csv", "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"\n{problem}.csv updated with {len(rows)} circuits.")
