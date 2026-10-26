"""G3: Pauli-path sweep at threshold 1e-3, two jobs in parallel, with a time limit.

Jobs are submitted asynchronously, at most 2 at a time; any job running longer
than 8 minutes is cancelled. The CSV is rewritten after every completed job so
a partial result is always available (missing qubits are written as 0.0).
Originally: run_g3_pauli_path.py
"""

import csv
import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

NUM_QUBITS = 36
BUDGET = 42.0  # cap on the real spend in $ (the per-job estimate was capped at $25 and useless)
MAX_JOB_S = 8 * 60  # cancel jobs running longer than 8 minutes
MAX_ACTIVE = 2

results = {q: 0.0 for q in range(NUM_QUBITS)}
active = {}  # qubit -> job_id
start = {}  # qubit -> submission time
total_spent = 0.0


def save_csv():
    with open("G3_pp.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for q in range(NUM_QUBITS):
            writer.writerow([f"Duke_G3_{q}", results[q]])
    print("-> G3_pp.csv updated.")


def poll_active():
    """Check every active job once: record finished ones, cancel slow ones."""
    global total_spent
    for q, job_id in list(active.items()):
        if time.time() - start.get(q, time.time()) > MAX_JOB_S:
            bq.cancel(job_id)
            del active[q]
            print(f"Qubit {q} too slow (> 8 min): cancelled")
            continue

        job = bq.get(job_id)
        if job.run_status not in ("RUNNING", "PENDING", "QUEUED"):
            value = getattr(job, "expectation_value", 0.0) or 0.0
            cost = getattr(job, "cost", 0.0) or 0.0
            results[q] = value
            total_spent += cost
            del active[q]
            print(f"Qubit {q} done | {value:.4f} | ${cost:.2f} | total ${total_spent:.2f}")
            save_csv()


print("G3 Pauli-path sweep...")

for q in range(NUM_QUBITS):
    if total_spent >= BUDGET:
        print("Budget reached, no more submissions.")
        break

    # Wait for a free slot
    while len(active) >= MAX_ACTIVE:
        poll_active()
        time.sleep(10)

    z = "I" * (NUM_QUBITS - 1 - q) + "Z" + "I" * q
    job = bq.run(f"Duke_G3_{q}", device="pauli-path", pauli_sum=[(z, 1.0)],
                 options={"pauli_path_truncation_threshold": 1e-3}, asynchronous=True)
    active[q] = job.job_id
    start[q] = time.time()
    print(f"Qubit {q} submitted (job {job.job_id})")

# Wait for the last jobs
while active:
    poll_active()
    time.sleep(10)

print("Sweep finished.")
