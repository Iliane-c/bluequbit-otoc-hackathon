"""Local Pauli-propagation simulator for the sample QASM files (no credits needed).

Idea: instead of evolving the 2^n state, evolve the observable Z_q backwards
through the circuit (Heisenberg picture), as a sum of Pauli strings:
  * CZ maps one Pauli string to one Pauli string (with a possible sign);
  * a single-qubit gate maps the local Pauli to a mix of X, Y, Z (up to 3 terms).
Terms with |coefficient| < threshold are dropped. At the end, only strings
made of I and Z have a non-zero expectation on |0...0>.

Each Pauli string is stored as two bit masks (x, z):
  I: x=0 z=0   X: x=1 z=0   Y: x=1 z=1   Z: x=0 z=1

Used to check S3 against the exact values (S3_0 reference: 0.1441).
Limitation of this version: duplicate merging packs (x, z) into one 64-bit key,
so it only works up to 32 qubits. The cleaned-up version in
otoc/pauli_propagation.py removes that limit and has tests.

Usage:
    python local_pauli_propagation.py <qasm_folder> [circuit=S3] [threshold=1e-5] [n_qubits=30]
Originally: test_3.py
"""

import math
import os
import re
import sys

import numpy as np

X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]])
Z = np.diag([1, -1]).astype(complex)
PAULIS = [X, Y, Z]  # index 0: X, 1: Y, 2: Z


def u3(theta, phi, lam):
    """OpenQASM u3 gate."""
    return np.array([
        [np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
        [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)],
    ])


def parse(path):
    """Parse a QASM file into ('u', qubit, matrix) and ('cz', a, b) operations."""
    ops = []
    for line in open(path):
        line = line.strip().rstrip(";")
        if not line or line.startswith(("OPENQASM", "include", "qreg")):
            continue
        name, args, targets = re.match(r"(\w+)(?:\((.*)\))?\s+(.*)", line).groups()
        # Angles look like "pi/2" or "-0.31"; evaluated with only `pi` in scope.
        args = [eval(a, {"pi": math.pi}) for a in args.split(",")] if args else []
        qubits = [int(x) for x in re.findall(r"q\[(\d+)\]", targets)]
        if name == "u3":
            ops.append(("u", qubits[0], u3(*args)))
        elif name == "x":
            ops.append(("u", qubits[0], X))
        elif name == "z":
            ops.append(("u", qubits[0], Z))
        elif name == "cz":
            ops.append(("cz", qubits[0], qubits[1]))
        else:
            raise ValueError(f"Unsupported gate {name}")
    return ops


def fuse(ops):
    """Merge consecutive single-qubit gates on the same qubit (fewer branching steps)."""
    out, pending = [], {}

    def flush(q):
        if q in pending:
            out.append(("u", q, pending.pop(q)))

    for op in ops:
        if op[0] == "u":
            q = op[1]
            pending[q] = op[2] @ pending[q] if q in pending else op[2]
        else:
            flush(op[1])
            flush(op[2])
            out.append(op)
    for q in list(pending):
        flush(q)
    return out


def ptm(U):
    """Pauli transfer matrix: U^dag P_i U = sum_j R[i, j] P_j."""
    R = np.zeros((3, 3))
    for i in range(3):
        M = U.conj().T @ PAULIS[i] @ U
        for j in range(3):
            R[i, j] = (0.5 * np.trace(PAULIS[j] @ M)).real
    return R


def expval(ops, n, q, thr, maxterms=None):
    """Return (<Z_q>, number of Pauli terms left) with truncation threshold `thr`."""
    ops = fuse(ops)
    one = np.uint64(1)
    xs = np.array([0], np.uint64)
    zs = np.array([1 << q], np.uint64)
    cs = np.array([1.0])

    for op in reversed(ops):
        if op[0] == "cz":
            # CZ conjugation: X_a -> X_a Z_b, X_b -> Z_a X_b, with a sign for XY / YX
            a, b = op[1], op[2]
            xa = (xs >> np.uint64(a)) & one
            xb = (xs >> np.uint64(b)) & one
            za = (zs >> np.uint64(a)) & one
            zb = (zs >> np.uint64(b)) & one
            sign = (xa & xb & (za ^ zb)).astype(bool)
            cs = np.where(sign, -cs, cs)
            zs = zs ^ (xb << np.uint64(a)) ^ (xa << np.uint64(b))
        else:
            # Single-qubit gate: expand the local Pauli with the transfer matrix
            k = op[1]
            R = ptm(op[2])
            sh = np.uint64(k)
            xk = (xs >> sh) & one
            zk = (zs >> sh) & one
            idx = np.where((xk == 0) & (zk == 1), 2,
                           np.where((xk == 1) & (zk == 0), 0,
                                    np.where((xk == 1) & (zk == 1), 1, -1)))
            ident = idx < 0
            nx, nz, nc = [xs[ident]], [zs[ident]], [cs[ident]]
            base_x = xs & ~(one << sh)
            base_z = zs & ~(one << sh)
            for i in range(3):
                sel = idx == i
                if not sel.any():
                    continue
                for j in range(3):
                    r = R[i, j]
                    if abs(r) < 1e-12:
                        continue
                    c = cs[sel] * r
                    keep = np.abs(c) >= thr
                    if not keep.any():
                        continue
                    bx = base_x[sel][keep]
                    bz = base_z[sel][keep]
                    if j == 0:
                        bx = bx | (one << sh)
                    elif j == 1:
                        bx = bx | (one << sh)
                        bz = bz | (one << sh)
                    else:
                        bz = bz | (one << sh)
                    nx.append(bx)
                    nz.append(bz)
                    nc.append(c[keep])
            xs, zs, cs = np.concatenate(nx), np.concatenate(nz), np.concatenate(nc)

            # Merge identical Pauli strings (key = x << 32 | z, valid for n <= 32)
            if len(cs) > 1:
                key = (xs << np.uint64(32)) | zs
                order = np.argsort(key, kind="stable")
                key, cs = key[order], cs[order]
                first = np.r_[True, key[1:] != key[:-1]]
                gid = np.cumsum(first) - 1
                cs = np.bincount(gid, weights=cs)
                key = key[first]
                xs = key >> np.uint64(32)
                zs = key & np.uint64(0xFFFFFFFF)
                m = np.abs(cs) >= thr
                xs, zs, cs = xs[m], zs[m], cs[m]

        if maxterms and len(cs) > maxterms:
            raise MemoryError(len(cs))

    # Only I/Z strings survive on |0...0>
    return float(cs[xs == 0].sum()), len(cs)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    circuit = sys.argv[2] if len(sys.argv) > 2 else "S3"
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-5
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 30

    rows = []
    for q in range(n):
        path = os.path.join(folder, f"Duke_{circuit}_{q}.qasm")
        if not os.path.exists(path):
            print("missing:", path)
            continue
        value, n_terms = expval(parse(path), n, q, thr)
        print(f"Duke_{circuit}_{q},{value:.8f}   ({n_terms} terms)", flush=True)
        rows.append((f"Duke_{circuit}_{q}", value))

    with open(f"{circuit}.csv", "w") as fh:
        fh.write("circuit_id,value\n")
        for cid, value in rows:
            fh.write(f"{cid},{value:.8f}\n")


if __name__ == "__main__":
    main()
