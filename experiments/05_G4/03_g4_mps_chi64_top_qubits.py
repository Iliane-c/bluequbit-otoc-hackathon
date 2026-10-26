"""G4: refine the 24 most significant qubits at chi=64, keep chi=32 for the others.

The qubits with the largest |<Z>| at chi=32 weigh the most in the correlation,
so they are recomputed first. A first job is submitted to read its estimated
cost; the run aborts if 24 such jobs would exceed $35. At most 4 jobs run at the
same time. The mixed CSV is rewritten every 15 seconds.
Originally: run_g4_smart_chi64.py
"""

import csv
import time

import bluequbit
import numpy as np
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 38
CHI = 64
WAIT_S = 70 * 60  # maximum run time
MAX_SPEND = 35.0  # budget cap in $
K = 24  # number of qubits to refine
MAX_CONCURRENT = 4  # below the hackathon limit of 5

# chi=32 baseline, used for the qubits that are not refined
try:
    v32 = np.loadtxt("G4_chi32.csv", delimiter=",", usecols=1)
except Exception as e:
    raise SystemExit(f"Could not load G4_chi32.csv ({e}); run 02_g4_mps_chi32_parallel.py first.")


def zs(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


# Largest |value| first
order = sorted(range(N), key=lambda q: -abs(v32[q]))[:K]


def submit(q):
    return bq.run(f"Duke_G4_{q}", device="mps.cpu", pauli_sum=[(zs(q), 1.0)],
                  options={"mps_bond_dimension": CHI}, asynchronous=True)


# Cost check on the first job
print(f"Submitting a first chi={CHI} job to read its estimated cost...")
first_q = order[0]
first_job = submit(first_q)
time.sleep(5)
est = getattr(bq.get(first_job.job_id), "estimated_cost", 0.0) or 0.79
print(f"Estimated cost per job: ${est:.2f} -> ~${est * K:.1f} for {K} jobs")

if est * K > MAX_SPEND:
    print(f"ABORT: estimated ${est * K:.1f} exceeds the ${MAX_SPEND} cap.")
    try:
        bq.cancel(first_job.job_id)
    except Exception:
        pass
    raise SystemExit("Aborted to protect the budget.")

active_jobs = {first_q: first_job}
pending = list(order[1:])
vals = {}
t0 = time.time()


def save():
    rows = [(f"Duke_G4_{q}", float(vals.get(q, v32[q]))) for q in range(N)]
    with open("G4_chi64_mix.csv", "w", newline="") as f:
        csv.writer(f).writerows(rows)


while time.time() - t0 < WAIT_S and len(vals) < K:
    # Collect finished jobs
    for q in list(active_jobs):
        try:
            job = bq.get(active_jobs[q].job_id)
            if job.ok:
                vals[q] = job.expectation_value
                print(f"Qubit {q} done at chi={CHI}: {vals[q]:.5f} | {len(vals)}/{K}")
                del active_jobs[q]
        except Exception as e:
            print(f"Status check failed for qubit {q}: {str(e)[:100]}")

    # Fill the free slots
    while len(active_jobs) < MAX_CONCURRENT and pending:
        q = pending.pop(0)
        try:
            active_jobs[q] = submit(q)
            print(f"Submitted qubit {q} ({len(active_jobs)}/{MAX_CONCURRENT} active)")
            time.sleep(2)
        except Exception:
            print(f"Submission rate-limited for qubit {q}, re-queued")
            pending.insert(0, q)
            break

    save()
    time.sleep(15)

# Cancel unfinished jobs
for q, job in active_jobs.items():
    if q not in vals:
        try:
            bq.cancel(job.job_id)
        except Exception:
            pass

save()
print("\nG4_chi64_mix.csv written.")
