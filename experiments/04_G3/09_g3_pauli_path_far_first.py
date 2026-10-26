"""G3: Pauli-path sweep at threshold 1e-4, easiest qubits first, until a hard deadline.

Lessons from the previous runs:
  * cost grows quickly near the butterfly (qubit 14), so qubits are submitted
    from the farthest (cheap) to the closest (expensive);
  * up to 4 jobs in parallel (hackathon limit: 5), 9-minute timeout per job;
  * a fixed deadline before the end of the hackathon; leftover jobs are
    cancelled and the partial CSV is kept.
Missing qubits are written as 0.0 and later replaced by MPS values
(10_g3_merge_mps_pauli_path.py).
Originally: run_g3_perfect.py
"""

import csv
import datetime as dt
import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N, THRESHOLD, MAX_PARALLEL, MAX_JOB_S = 36, 1e-4, 4, 9 * 60
DEADLINE = dt.datetime(2026, 10, 25, 15, 15, tzinfo=dt.timezone.utc)  # 16:15 Paris time


def zs(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


def dist(q):
    """Manhattan distance to the butterfly qubit 14 (row 2, col 2) on the 6x6 grid."""
    return abs(q // 6 - 2) + abs(q % 6 - 2)


def now():
    return dt.datetime.now(dt.timezone.utc)


queue = sorted(range(N), key=lambda q: -dist(q))  # farthest (easiest) first
results, active, start = {}, {}, {}


def save():
    with open("G3_pp.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for q in range(N):
            writer.writerow([f"Duke_G3_{q}", float(results.get(q, 0.0))])


print("G3 Pauli-path sweep, far qubits first...")

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
            print(f"Qubit {q}: {results[q]:.5f} | {len(results)}/{N} done", flush=True)
        elif job.run_status not in ("RUNNING", "PENDING", "QUEUED"):
            del active[q]
            print(f"Qubit {q} failed: {job.run_status}")
        elif time.time() - start[q] > MAX_JOB_S:
            try:
                bq.cancel(job_id)
            except Exception:
                pass
            del active[q]
            print(f"Qubit {q} too slow, cancelled")

    # Fill the free slots
    while queue and len(active) < MAX_PARALLEL:
        q = queue.pop(0)
        try:
            job = bq.run(f"Duke_G3_{q}", device="pauli-path", pauli_sum=[(zs(q), 1.0)],
                         options={"pauli_path_truncation_threshold": THRESHOLD},
                         asynchronous=True)
            active[q] = job.job_id
            start[q] = time.time()
            print(f"Submitted qubit {q} (job {job.job_id})")
        except Exception as e:
            print(f"Could not submit qubit {q}: {str(e)[:120]}")
            if "LIMIT" in str(e):  # parallel-jobs limit: retry later
                queue.insert(0, q)
                break

    time.sleep(10)

# Cancel whatever is still running at the deadline
for q, job_id in active.items():
    try:
        bq.cancel(job_id)
    except Exception:
        pass

save()
print(f"G3_pp.csv ready: {len(results)} qubits computed.")
