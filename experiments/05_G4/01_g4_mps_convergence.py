"""G4 (38 qubits, 2D grid of Haar-random gates): MPS convergence test on witness qubits.

Runs qubits 0 (butterfly corner), 21 (middle) and 37 (extra row, far away)
at chi = 16, 32, 64, 128 and checks whether the values stabilise when chi
doubles, with a $3 cap for the whole test.
Result: qubit 0 moved from 0.270 (chi=32) to 0.098 (chi=64), i.e. MPS is far
from converged on this 2D circuit.
Originally: test_g4_convergence.py
"""

import time

import bluequbit
from dotenv import load_dotenv

load_dotenv()
bq = bluequbit.init()

N = 38

print("Circuit info for Duke_G4_0:")
try:
    print(bq.get_circuit_info("Duke_G4_0"))
except Exception as e:
    print(f"Not available: {e}")


def zstr(q):
    return "I" * (N - 1 - q) + "Z" + "I" * q


def run_one(q, device, options, timeout=600):
    """Return (value, cost, seconds) for one qubit."""
    t0 = time.time()
    job = bq.run(f"Duke_G4_{q}", device=device, pauli_sum=[(zstr(q), 1.0)],
                 options=options, timeout=timeout)
    cost = getattr(job, "cost", 0.0) or 0.0
    return job.expectation_value, cost, round(time.time() - t0, 1)


WITNESSES = (0, 21, 37)
configs = [("mps.cpu", {"mps_bond_dimension": chi}) for chi in (16, 32, 64, 128)]

spent = 0.0
print("\nConvergence test on witness qubits", WITNESSES)

for device, options in configs:
    row = []
    for q in WITNESSES:
        try:
            value, cost, seconds = run_one(q, device, options)
        except Exception as e:
            raise SystemExit(f"Stopping on error: {str(e)[:200]}")
        spent += cost
        row.append(round(value, 4))
        print(f"{device} {options} | qubit {q} | {value:.4f} | ${cost:.4f} | {seconds}s")

    print(f"  -> values {row} | total spent ${spent:.3f}\n")
    if spent > 3.0:
        print("Test budget of $3.00 reached, stopping.")
        break

print("Done. Check whether the values stabilise as chi doubles.")
