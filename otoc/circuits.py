"""Static metadata about the challenge circuits and helpers to address them.

Every circuit has one hidden program per qubit, identified as
``Duke_<circuit>_<qubit>``. For each of them we estimate <Z_q>, the expectation
value of Pauli Z on qubit ``q`` after running the program from |0...0>.
"""

from __future__ import annotations

from dataclasses import dataclass

GRID_COLUMNS = 6


@dataclass(frozen=True)
class CircuitSpec:
    """Description of one challenge circuit, as published by the organizers."""

    name: str
    num_qubits: int
    layout: str  # "chain" (1D) or "grid" (rows of GRID_COLUMNS qubits)
    butterfly: int  # qubit where the perturbation ("butterfly") is applied
    points: int  # maximum score for this problem
    description: str


CIRCUITS: dict[str, CircuitSpec] = {
    spec.name: spec
    for spec in (
        CircuitSpec("S1", 4, "chain", 0, 100,
                    "1D chain, Haar-random 2-qubit gates, 4 layers in U"),
        CircuitSpec("S2", 16, "chain", 0, 100,
                    "1D chain, Haar-random 2-qubit gates, 12 layers in U"),
        CircuitSpec("S3", 30, "grid", 14, 100,
                    "5x6 grid, random 2-qubit Cliffords (+ some Rz), 16 layers in U"),
        CircuitSpec("G1", 30, "chain", 0, 300,
                    "1D chain, Haar-random 2-qubit gates, 32 layers in U"),
        CircuitSpec("G2", 36, "chain", 18, 600,
                    "1D chain, Haar-random 2-qubit gates, 18 layers in U"),
        CircuitSpec("G3", 36, "grid", 14, 800,
                    "6x6 grid, random 2-qubit Cliffords (+ some Rz), 24 layers in U"),
        CircuitSpec("G4", 38, "grid", 0, 1000,
                    "6x6 grid + qubits 36-37 below 30-31, Haar-random gates, 16 layers in U"),
    )
}


def get_spec(circuit: str) -> CircuitSpec:
    """Return the spec of ``circuit`` (case-insensitive), e.g. ``get_spec("g3")``."""
    try:
        return CIRCUITS[circuit.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown circuit {circuit!r}; expected one of {list(CIRCUITS)}") from exc


def circuit_id(circuit: str, qubit: int) -> str:
    """BlueQubit identifier of the program measured on ``qubit``."""
    return f"Duke_{circuit.upper()}_{qubit}"


def z_observable(num_qubits: int, qubit: int) -> str:
    """Pauli string with a single Z on ``qubit``.

    BlueQubit uses little-endian ordering: qubit 0 is the *rightmost*
    character. Getting this wrong permutes the answers and ruins the score.
    """
    if not 0 <= qubit < num_qubits:
        raise ValueError(f"qubit {qubit} out of range for {num_qubits} qubits")
    return "I" * (num_qubits - 1 - qubit) + "Z" + "I" * qubit


def coordinates(spec: CircuitSpec, qubit: int) -> tuple[int, int]:
    """(row, column) of ``qubit`` on the device layout.

    For grids, qubit = row * 6 + col. G4's two extra qubits (36, 37) form a
    partial row under qubits 30 and 31, i.e. they sit at row 6, columns 0-1;
    the formula covers this case as well.
    """
    if spec.layout == "chain":
        return 0, qubit
    return divmod(qubit, GRID_COLUMNS)


def distance_to_butterfly(spec: CircuitSpec, qubit: int) -> int:
    """Manhattan distance between ``qubit`` and the butterfly qubit.

    Qubits far from the butterfly see little scrambling, so their simulations
    are much cheaper. This is used to schedule the easy jobs first.
    """
    r0, c0 = coordinates(spec, spec.butterfly)
    r, c = coordinates(spec, qubit)
    return abs(r - r0) + abs(c - c0)
