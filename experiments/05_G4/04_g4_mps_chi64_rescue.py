"""G4: recover the chi=64 jobs left running by the previous script, then continue.

The previous run was interrupted while 5 jobs were still running on BlueQubit
(they keep running, and billing, after the script stops). This script:
  1. checks those orphan jobs by ID and keeps any result that is ready;
  2. reuses the chi=64 values already known from the convergence test;
  3. resumes the top-24 refinement with up to 5 jobs in parallel, for 55 minutes.
Originally: run_g4_rescue.py
"""

import csv
import time

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N, CHI, K, LIMIT = 38, 64, 24, 5
WAIT_S = 55 * 60  # finish well before the deadline

# Job IDs left running by 03_g4_mps_chi64_top_qubits.py
ORPHANS = [
    "j9qsTsLDSCihEhgX",
    "cXljjoMs9ICGXr3j",
    "c3jQSFutFoXROrvQ",
    "5UxRIQ3LF9aLtd96",
    "04Nm3etAZKqlNU6f",
]

# chi=32 baseline, used for the qubits that are not refined
try:
    v32 = np.loadtxt("G4_chi32.csv", delimiter=",", usecols=1)
except Exception as e:
    raise SystemExit(f"Could not load G4_chi32.csv ({e}); run 02_g4_mps_chi32_parallel.py first.")


def zs(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


targets = sorted(range(N), key=lambda q: -abs(v32[q]))[:K]

# chi=64 values already known from 01_g4_mps_convergence.py
vals = {0: 0.0978, 21: -0.0042, 37: 0.9749}
active = {}  # qubit -> job_id

print("Checking orphan jobs...")
for job_id in ORPHANS:
    try:
        job = bq.get(job_id)
        q = int(job.stored_circuit_id.split("_")[-1])
        if job.ok and job.status == "COMPLETED":
            vals[q] = job.expectation_value
            print(f"Orphan qubit {q} already finished: {vals[q]:.5f}")
        elif job.run_status in ("RUNNING", "PENDING", "QUEUED"):
            active[q] = job_id
            print(f"Orphan qubit {q} still {job.run_status}")
        else:
            print(f"Orphan job {job_id} unusable: {job.run_status}")
    except Exception as e:
        print(f"Could not fetch orphan {job_id}: {str(e)[:80]}")

queue = [q for q in targets if q not in vals and q not in active]
print(f"Known: {sorted(vals)} | active: {list(active)} | queued: {len(queue)}")


def save():
    rows = [(f"Duke_G4_{q}", float(vals.get(q, v32[q]))) for q in range(N)]
    with open("G4_chi64_mix.csv", "w", newline="") as f:
        csv.writer(f).writerows(rows)


t0 = time.time()
while time.time() - t0 < WAIT_S and (queue or active):
    # Collect finished jobs
    for q, job_id in list(active.items()):
        try:
            job = bq.get(job_id)
            if job.ok and job.status == "COMPLETED":
                vals[q] = job.expectation_value
                del active[q]
                print(f"Qubit {q} done at chi={CHI}: {vals[q]:.5f}")
            elif job.run_status not in ("RUNNING", "PENDING", "QUEUED"):
                print(f"Qubit {q} failed: {job.run_status}")
                del active[q]
        except Exception:
            pass

    # Fill the free slots
    while queue and len(active) < LIMIT:
        q = queue[0]
        try:
            job = bq.run(f"Duke_G4_{q}", device="mps.cpu", pauli_sum=[(zs(q), 1.0)],
                         options={"mps_bond_dimension": CHI}, asynchronous=True)
            active[q] = job.job_id
            queue.pop(0)
            print(f"Submitted qubit {q} (job {job.job_id})")
            time.sleep(2)
        except Exception as e:
            if "PARALLEL_JOBS_LIMIT" not in str(e):
                print(f"Submission error for qubit {q}: {str(e)[:120]}")
            break

    save()
    print(f"Progress: {len(vals)} at chi=64 | {len(active)} active | {len(queue)} queued",
          flush=True)
    time.sleep(25)

# Never leave jobs running behind
for q, job_id in list(active.items()):
    try:
        bq.cancel(job_id)
    except Exception:
        pass

save()
print("\nG4_chi64_mix.csv written.")
