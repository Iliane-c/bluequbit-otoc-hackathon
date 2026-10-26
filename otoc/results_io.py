"""Reading and writing submission files.

A submission is a CSV with one ``circuit_id,value`` row per qubit, e.g.::

    circuit_id,value
    Duke_G3_0,-0.0147
    Duke_G3_1,-0.0011
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Mapping
from pathlib import Path

from .circuits import circuit_id

log = logging.getLogger(__name__)

HEADER = ("circuit_id", "value")


def read_results(path: str | Path) -> dict[int, float]:
    """Read a submission CSV and return ``{qubit: value}``.

    The header line is optional, so files written with or without it both work.
    """
    values: dict[int, float] = {}
    with open(path, newline="") as handle:
        for row in csv.reader(handle):
            if len(row) != 2 or row[0] == HEADER[0]:
                continue
            qubit = int(row[0].rsplit("_", 1)[1])
            values[qubit] = float(row[1])
    return values


def write_results(
    path: str | Path,
    circuit: str,
    num_qubits: int,
    values: Mapping[int, float],
    fallback: Mapping[int, float] | None = None,
    default: float = 0.0,
    warn: bool = True,
) -> list[int]:
    """Write a complete submission file for ``circuit``.

    Missing qubits are taken from ``fallback`` when available, otherwise set to
    ``default`` (logged as a warning when ``warn`` is true). The submission
    portal rejects files with missing IDs, so the file always contains every
    qubit.

    Returns:
        The qubits that had no value and were filled with ``default``.
    """
    fallback = fallback or {}
    filled_with_default = []
    rows = []
    for qubit in range(num_qubits):
        if qubit in values:
            value = values[qubit]
        elif qubit in fallback:
            value = fallback[qubit]
        else:
            value = default
            filled_with_default.append(qubit)
        rows.append((circuit_id(circuit, qubit), float(value)))

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)

    if filled_with_default and warn:
        log.warning("%s: qubits %s have no value and were set to %s",
                    path.name, filled_with_default, default)
    return filled_with_default
