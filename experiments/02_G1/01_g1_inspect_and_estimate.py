"""G1 (30 qubits, deep 1D chain): inspect the circuit and estimate cost before running.

`get_circuit_info` and `estimate` are free, so this decides between CPU and GPU
without spending credits.
Originally: verif1.py
"""

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

ids = [f"Duke_G1_{q}" for q in range(30)]

print("Circuit info for Duke_G1_0:")
try:
    print(bq.get_circuit_info(ids[0]))
except Exception as e:
    print(f"Error fetching circuit info: {e}")

print("\nEstimated runtime and cost:")
for device in ("cpu", "gpu"):
    try:
        est = bq.estimate(ids[0], device=device)
        print(f"{device.upper()}: ~{est.estimated_runtime} ms, ~${est.estimated_cost}")
        if est.warning_message:
            print(f"  warning: {est.warning_message}")
    except Exception as e:
        print(f"Error estimating on {device}: {e}")
