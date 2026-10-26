"""G3: replace MPS values by the Pauli-path (1e-4) values that finished in time.

The Pauli-path sweep did not complete before the deadline, so the submission
mixes both: MPS for most qubits, Pauli path where available. The values are
copied from the output of 09_g3_pauli_path_far_first.py.
Originally: merge_g3.py
"""

import csv

# MPS baseline
mps = {}
try:
    with open("G3.csv") as f:
        for row in csv.reader(f):
            if len(row) == 2:
                mps[row[0]] = float(row[1])
except Exception as e:
    print("Could not read G3.csv:", e)

# Pauli-path values (threshold 1e-4) that completed
pauli_path_values = {
    0: -0.014754238770955167,
    1: -0.0011426164136740641,
    3: -0.0007745932437923157,
    4: 0.0028645719246939965,
    30: -0.034283233477829654,
    31: 0.060335317018704746,
}

for q, value in pauli_path_values.items():
    mps[f"Duke_G3_{q}"] = value

with open("G3_merge.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for q in range(36):
        key = f"Duke_G3_{q}"
        writer.writerow([key, mps.get(key, 0.0)])

print("G3_merge.csv written.")
