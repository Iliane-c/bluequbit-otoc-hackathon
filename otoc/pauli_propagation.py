"""Local Pauli-propagation simulator for the open sample circuits (QASM files).

We want <0|C^dag Z_q C|0>. Instead of evolving the state, we evolve the
observable backwards through the circuit (Heisenberg picture):

    O  <-  G^dag O G      for each gate G, from the last one to the first.

The observable is stored as a sum of Pauli strings with real coefficients.

* A CZ maps a Pauli string to a single Pauli string (Clifford), so the number
  of terms does not change.
* A single-qubit gate maps the local Pauli on that qubit to a combination of
  X, Y and Z, which can multiply the number of terms by up to 3.

Terms whose |coefficient| falls below ``threshold`` are dropped; this is the
only approximation. At the end, <0...0|P|0...0> is 1 if P contains only I and Z
and 0 otherwise, so the answer is the sum of the coefficients of the
"X-free" strings.

Each Pauli string is encoded by two bit masks (x, z), stored as uint64, so the
simulator supports up to 64 qubits:

    I: x=0 z=0    X: x=1 z=0    Y: x=1 z=1    Z: x=0 z=1
"""

from __future__ import annotations

import ast
import math
import operator
import re
from pathlib import Path

import numpy as np

PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z = np.array([[1, 0], [0, -1]], dtype=complex)
PAULIS = (PAULI_X, PAULI_Y, PAULI_Z)  # index 0: X, 1: Y, 2: Z

ONE = np.uint64(1)

# A gate is either ("1q", qubit, 2x2 matrix) or ("cz", qubit_a, qubit_b).
Gate = tuple


# --------------------------------------------------------------------------- #
# QASM parsing
# --------------------------------------------------------------------------- #

_BINARY_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
               ast.Mult: operator.mul, ast.Div: operator.truediv}


def _eval_angle(expression: str) -> float:
    """Safely evaluate a QASM angle such as ``-3*pi/4`` (no ``eval``)."""

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "pi":
            return math.pi
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
            return _BINARY_OPS[type(node.op)](walk(node.left), walk(node.right))
        raise ValueError(f"Unsupported angle expression: {expression!r}")

    return walk(ast.parse(expression.strip(), mode="eval"))


def u3_matrix(theta: float, phi: float, lam: float) -> np.ndarray:
    """OpenQASM ``u3(theta, phi, lambda)`` gate."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array([
        [c, -np.exp(1j * lam) * s],
        [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c],
    ])


_INSTRUCTION = re.compile(r"(\w+)(?:\((.*)\))?\s+(.*)")


def parse_qasm(path: str | Path) -> list[Gate]:
    """Parse an OpenQASM 2.0 file restricted to the gates used in the challenge
    (``u3``, ``cz``, ``x``, ``z``)."""
    gates: list[Gate] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip().rstrip(";")
        if not line or line.startswith(("OPENQASM", "include", "qreg", "creg", "//")):
            continue
        name, args, targets = _INSTRUCTION.match(line).groups()
        params = [_eval_angle(a) for a in args.split(",")] if args else []
        qubits = [int(q) for q in re.findall(r"\[(\d+)\]", targets)]
        if name == "u3":
            gates.append(("1q", qubits[0], u3_matrix(*params)))
        elif name == "x":
            gates.append(("1q", qubits[0], PAULI_X))
        elif name == "z":
            gates.append(("1q", qubits[0], PAULI_Z))
        elif name == "cz":
            gates.append(("cz", qubits[0], qubits[1]))
        else:
            raise ValueError(f"Unsupported gate {name!r} in {path}")
    return gates


def fuse_single_qubit_gates(gates: list[Gate]) -> list[Gate]:
    """Merge consecutive single-qubit gates acting on the same qubit.

    Fewer single-qubit gates means fewer branching steps during propagation.
    """
    fused: list[Gate] = []
    pending: dict[int, np.ndarray] = {}

    def flush(qubit: int) -> None:
        if qubit in pending:
            fused.append(("1q", qubit, pending.pop(qubit)))

    for gate in gates:
        if gate[0] == "1q":
            _, qubit, matrix = gate
            # The later gate acts after the earlier one: U_total = U_new @ U_old.
            pending[qubit] = matrix @ pending[qubit] if qubit in pending else matrix
        else:
            flush(gate[1])
            flush(gate[2])
            fused.append(gate)
    for qubit in list(pending):
        flush(qubit)
    return fused


# --------------------------------------------------------------------------- #
# Propagation
# --------------------------------------------------------------------------- #

def pauli_transfer_matrix(unitary: np.ndarray) -> np.ndarray:
    """R[i, j] such that U^dag P_i U = sum_j R[i, j] P_j, for P in (X, Y, Z)."""
    matrix = np.zeros((3, 3))
    for i, p_in in enumerate(PAULIS):
        conjugated = unitary.conj().T @ p_in @ unitary
        for j, p_out in enumerate(PAULIS):
            matrix[i, j] = 0.5 * np.trace(p_out @ conjugated).real
    return matrix


def _bit(masks: np.ndarray, qubit: int) -> np.ndarray:
    return (masks >> np.uint64(qubit)) & ONE


def _apply_cz(xs, zs, coeffs, a: int, b: int):
    """Conjugate every Pauli string by CZ(a, b): X_a -> X_a Z_b, X_b -> Z_a X_b."""
    xa, xb = _bit(xs, a), _bit(xs, b)
    za, zb = _bit(zs, a), _bit(zs, b)
    # A minus sign appears for X_a Y_b and Y_a X_b (and their mirror images).
    flip = (xa & xb & (za ^ zb)).astype(bool)
    coeffs = np.where(flip, -coeffs, coeffs)
    zs = zs ^ (xb << np.uint64(a)) ^ (xa << np.uint64(b))
    return xs, zs, coeffs


def _apply_single_qubit(xs, zs, coeffs, qubit: int, unitary: np.ndarray, threshold: float):
    """Conjugate every Pauli string by a single-qubit gate and truncate."""
    transfer = pauli_transfer_matrix(unitary)
    shift = np.uint64(qubit)
    mask = ONE << shift
    x_bit, z_bit = _bit(xs, qubit), _bit(zs, qubit)
    # Local Pauli on this qubit: -1 = I, 0 = X, 1 = Y, 2 = Z.
    local = np.select([(x_bit == 1) & (z_bit == 0), (x_bit == 1) & (z_bit == 1),
                       (x_bit == 0) & (z_bit == 1)], [0, 1, 2], default=-1)

    identity = local < 0
    out_x, out_z, out_c = [xs[identity]], [zs[identity]], [coeffs[identity]]
    base_x, base_z = xs & ~mask, zs & ~mask

    for i in range(3):
        selected = local == i
        if not selected.any():
            continue
        for j in range(3):
            if abs(transfer[i, j]) < 1e-12:
                continue
            new_c = coeffs[selected] * transfer[i, j]
            keep = np.abs(new_c) >= threshold
            if not keep.any():
                continue
            new_x, new_z = base_x[selected][keep], base_z[selected][keep]
            if j in (0, 1):  # X or Y
                new_x = new_x | mask
            if j in (1, 2):  # Y or Z
                new_z = new_z | mask
            out_x.append(new_x)
            out_z.append(new_z)
            out_c.append(new_c[keep])

    return np.concatenate(out_x), np.concatenate(out_z), np.concatenate(out_c)


def _merge_duplicates(xs, zs, coeffs, threshold: float):
    """Add up the coefficients of identical Pauli strings, then truncate."""
    if len(coeffs) < 2:
        return xs, zs, coeffs
    order = np.lexsort((zs, xs))
    xs, zs, coeffs = xs[order], zs[order], coeffs[order]
    is_first = np.r_[True, (xs[1:] != xs[:-1]) | (zs[1:] != zs[:-1])]
    group = np.cumsum(is_first) - 1
    coeffs = np.bincount(group, weights=coeffs)
    xs, zs = xs[is_first], zs[is_first]
    keep = np.abs(coeffs) >= threshold
    return xs[keep], zs[keep], coeffs[keep]


def expectation_z(gates: list[Gate], qubit: int, threshold: float = 1e-5,
                  max_terms: int | None = None) -> tuple[float, int]:
    """Approximate <0|C^dag Z_qubit C|0> by truncated Pauli propagation.

    Args:
        gates: circuit, as returned by :func:`parse_qasm`.
        qubit: qubit on which Z is measured.
        threshold: drop Pauli terms whose |coefficient| is below this value.
            Smaller is more accurate and slower; 0 gives the exact value.
        max_terms: abort with ``MemoryError`` if the expansion exceeds this size.

    Returns:
        (expectation value, number of Pauli terms left at the end)
    """
    xs = np.array([0], dtype=np.uint64)
    zs = np.array([1 << qubit], dtype=np.uint64)
    coeffs = np.array([1.0])

    for gate in reversed(fuse_single_qubit_gates(gates)):
        if gate[0] == "cz":
            xs, zs, coeffs = _apply_cz(xs, zs, coeffs, gate[1], gate[2])
        else:
            xs, zs, coeffs = _apply_single_qubit(xs, zs, coeffs, gate[1], gate[2], threshold)
            xs, zs, coeffs = _merge_duplicates(xs, zs, coeffs, threshold)
        if max_terms is not None and len(coeffs) > max_terms:
            raise MemoryError(f"{len(coeffs)} Pauli terms exceed max_terms={max_terms}")

    # Only strings made of I and Z have a non-zero expectation value on |0...0>.
    return float(coeffs[xs == 0].sum()), len(coeffs)
