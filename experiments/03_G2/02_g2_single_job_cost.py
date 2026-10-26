"""G2: measure the real cost and runtime of ONE MPS job at a given bond dimension.

Run on the butterfly qubit (18, the most entangled one) before launching a full
sweep. Used with chi = 8, 16, 32 and 64 (originally four near-identical
scripts: test_g2_single.py, test_g2_chi16.py, test_g2_chi32.py, test_g2_chi64.py).

    python g2_single_job_cost.py 16
"""

import sys

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

CHI = int(sys.argv[1]) if len(sys.argv) > 1 else 8
n = 36
q = 18
z = "I" * (n - 1 - q) + "Z" + "I" * q

print(f"Single test job on Duke_G2_{q} (mps.cpu, chi={CHI})...")
try:
    job = bq.run(f"Duke_G2_{q}", device="mps.cpu", pauli_sum=[(z, 1.0)],
                 options={"mps_bond_dimension": CHI}, timeout=120)
    print(f"<Z>      : {job.expectation_value}")
    print(f"Cost     : ${getattr(job, 'cost', 0.0)}")
    print(f"Run time : {getattr(job, 'run_time_ms', 0)} ms")
    print(f"Status   : {getattr(job, 'run_status', 'UNKNOWN')}")
except Exception as e:
    print(f"Error or timeout: {e}")
