"""Benchmark Pauli-path thresholds on a known sample and on a G3 qubit.

S3 is also a Clifford grid and its exact value is known (Duke_S3_0 = 0.1441),
so it shows how accurate each threshold is; G3_35 (far from the butterfly)
shows how long each threshold takes on the graded circuit. Jobs are cancelled
after 5 minutes.
Originally: test_thresholds.py
"""

import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()


def zs(n, q):
    return "I" * (n - 1 - q) + "Z" + "I" * q


def run(cid, n, q, threshold):
    """Return (value, cost, seconds), or a 'cancelled' marker after 5 minutes."""
    t0 = time.time()
    job = bq.run(cid, device="pauli-path", pauli_sum=[(zs(n, q), 1.0)],
                 options={"pauli_path_truncation_threshold": threshold}, asynchronous=True)
    while time.time() - t0 < 300:
        result = bq.get(job.job_id)
        if result.run_status not in ("RUNNING", "PENDING", "QUEUED"):
            value = getattr(result, "expectation_value", 0.0) or 0.0
            cost = getattr(result, "cost", 0.0) or 0.0
            return value, cost, round(time.time() - t0, 1)
        time.sleep(5)
    try:
        bq.cancel(job.job_id)
    except Exception:
        pass
    return "cancelled (> 5 min)", None, 300


for threshold in (1e-3, 1e-4, 1e-5):
    print("S3_0  (ref 0.1441) | threshold", threshold, ":", run("Duke_S3_0", 30, 0, threshold))
    print("G3_35              | threshold", threshold, ":", run("Duke_G3_35", 36, 35, threshold),
          flush=True)
