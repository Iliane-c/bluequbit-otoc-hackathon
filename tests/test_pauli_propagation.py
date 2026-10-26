"""Check the local Pauli-propagation simulator against an exact state vector."""

import numpy as np
import pytest

from otoc.pauli_propagation import (PAULI_X, PAULI_Z, expectation_z,
                                    fuse_single_qubit_gates, parse_qasm, u3_matrix)


def random_circuit(num_qubits: int, depth: int, rng: np.random.Generator):
    gates = []
    for layer in range(depth):
        for q in range(num_qubits):
            gates.append(("1q", q, u3_matrix(*rng.uniform(0, 2 * np.pi, 3))))
        if layer % 3 == 0:
            gates.append(("1q", int(rng.integers(num_qubits)), PAULI_X))
            gates.append(("1q", int(rng.integers(num_qubits)), PAULI_Z))
        for q in range(layer % 2, num_qubits - 1, 2):
            gates.append(("cz", q, q + 1))
    return gates


def exact_expectation_z(gates, num_qubits: int, qubit: int) -> float:
    """Dense state-vector reference. Qubit q is bit q of the basis index."""
    state = np.zeros(2 ** num_qubits, dtype=complex)
    state[0] = 1.0
    state = state.reshape([2] * num_qubits)  # axis k <-> qubit num_qubits-1-k
    axis = lambda q: num_qubits - 1 - q  # noqa: E731
    for gate in gates:
        if gate[0] == "1q":
            _, q, u = gate
            state = np.moveaxis(np.tensordot(u, state, axes=([1], [axis(q)])), 0, axis(q))
        else:
            _, a, b = gate
            index = [slice(None)] * num_qubits
            index[axis(a)], index[axis(b)] = 1, 1
            state[tuple(index)] *= -1
    probs = np.abs(state) ** 2
    signs = np.where(np.arange(2 ** num_qubits) >> qubit & 1, -1.0, 1.0)
    return float(probs.reshape(-1) @ signs)


@pytest.mark.parametrize("seed", range(5))
def test_matches_state_vector(seed):
    rng = np.random.default_rng(seed)
    n = 5
    gates = random_circuit(n, depth=6, rng=rng)
    for q in range(n):
        approx, _ = expectation_z(gates, q, threshold=0.0)
        assert approx == pytest.approx(exact_expectation_z(gates, n, q), abs=1e-9)


def test_fusion_preserves_circuit():
    rng = np.random.default_rng(42)
    n = 4
    gates = random_circuit(n, depth=4, rng=rng)
    fused = fuse_single_qubit_gates(gates)
    assert len(fused) < len(gates)
    for q in range(n):
        assert exact_expectation_z(fused, n, q) == pytest.approx(exact_expectation_z(gates, n, q))


def test_parse_qasm(tmp_path):
    qasm = tmp_path / "c.qasm"
    qasm.write_text('OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
                    "u3(pi/2,-pi/4,0.5) q[0];\ncz q[0],q[1];\nx q[1];\nz q[0];\n")
    gates = parse_qasm(qasm)
    assert [g[0] for g in gates] == ["1q", "cz", "1q", "1q"]
    for q in range(2):
        approx, _ = expectation_z(gates, q, threshold=0.0)
        assert approx == pytest.approx(exact_expectation_z(gates, 2, q))


def test_large_qubit_index():
    """Masks are 64-bit: qubits beyond 32 (G3/G4 have 36-38) must work."""
    gates = [("1q", 37, u3_matrix(0.3, 0.0, 0.0)), ("cz", 36, 37)]
    value, _ = expectation_z(gates, 37, threshold=0.0)
    assert value == pytest.approx(np.cos(0.3))
