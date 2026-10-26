"""Smoke test of the BlueQubit SDK on a known circuit, before the challenge started.

Runs a 5-qubit Quantum Fourier Transform on the CPU simulator and prints the counts.
Requires qiskit. Originally: run_s1.py
"""

import bluequbit
from qiskit.circuit.library import QFT

# 5-qubit QFT, measured on all qubits
qft_circuit = QFT(num_qubits=5)
qft_circuit.measure_all()

# Uses BLUEQUBIT_API_TOKEN from the environment
bq = bluequbit.init()

result = bq.run(qft_circuit, job_name="QFT on CPU")
print(result.get_counts())
