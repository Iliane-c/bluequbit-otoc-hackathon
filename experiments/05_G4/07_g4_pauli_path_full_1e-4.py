"""G4: full Pauli-path sweep at threshold 1e-4, far qubits first, until a deadline.

Same scheduler as G3 (09_g3_pauli_path_far_first.py), adapted to G4: the
butterfly is qubit 0 (corner), and qubits 36-37 sit in a partial row below.
Qubit 0 was already computed by 06_g4_pauli_path_q0_1e-4.py and returned 0.0.

Outcome: the grid qubits that completed also returned exactly 0. At this
threshold every Pauli path is truncated on this Haar-random 2D circuit, so the
result is useless (all-equal values score 0).
Originally: run_g4_full_1e4.py
"""

import csv
import datetime as dt
import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N, THRESHOLD, MAX_PARALLEL, MAX_JOB_S = 38, 1e-4, 4, 8 * 60
DEADLINE = dt.datetime(2026, 10, 25, 15, 25, tzinfo=dt.timezone.utc)


def zs(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


def dist(q):
    """Approximate distance to the butterfly qubit 0 (corner of the grid)."""
    if q < 36:
        return (q // 6) + (q % 6)
    return 5 + (q - 36)  # extra qubits 36-37


def now():
    return dt.datetime.now(dt.timezone.utc)


queue = sorted(range(N), key=lambda q: -dist(q))  # farthest (easiest) first
results, active, start = {}, {}, {}

# Qubit 0 is already known from the single-qubit test
results[0] = 0.0
queue.remove(0)


def save():
    with open("G4_pp.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for q in range(N):
            writer.writerow([f"Duke_G4_{q}", float(results.get(q, 0.0))])


save()
print("G4 Pauli-path sweep (38 qubits, threshold 1e-4)...")

while (queue or active) and now() < DEADLINE:
    # Collect finished jobs, cancel slow ones
    for q, job_id in list(active.items()):
        try:
            job = bq.get(job_id)
        except Exception:
            continue
        if job.run_status == "COMPLETED":
            results[q] = job.expectation_value
            del active[q]
            save()
            print(f"G4 qubit {q}: {results[q]:.5f} | {len(results)}/{N} done", flush=True)
        elif job.run_status not in ("RUNNING", "PENDING", "QUEUED"):
            del active[q]
            print(f"G4 qubit {q} failed: {job.run_status}")
        elif time.time() - start[q] > MAX_JOB_S:
            try:
                bq.cancel(job_id)
            except Exception:
                pass
            del active[q]
            print(f"G4 qubit {q} too slow, cancelled")

    # Fill the free slots
    while queue and len(active) < MAX_PARALLEL:
        q = queue.pop(0)
        try:
            job = bq.run(f"Duke_G4_{q}", device="pauli-path", pauli_sum=[(zs(q), 1.0)],
                         options={"pauli_path_truncation_threshold": THRESHOLD},
                         asynchronous=True)
            active[q] = job.job_id
            start[q] = time.time()
            print(f"G4 submitted qubit {q} (job {job.job_id})")
        except Exception as e:
            print(f"G4 could not submit qubit {q}: {str(e)[:100]}")
            if "LIMIT" in str(e):  # parallel-jobs limit: retry later
                queue.insert(0, q)
                break

    time.sleep(10)

for q, job_id in active.items():
    try:
        bq.cancel(job_id)
    except Exception:
        pass

save()
print(f"G4_pp.csv written: {len(results)} qubits computed.")
