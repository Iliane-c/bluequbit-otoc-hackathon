"""Simulate the open sample circuits locally with Pauli propagation (no credits).

The sample problems (S1-S3) come with one QASM file per qubit. This script
runs the local Pauli-propagation simulator on each file and writes a
submission CSV:

    python scripts/simulate_local.py path/to/qasm_folder S3 --threshold 1e-5
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.circuits import CIRCUITS, circuit_id, get_spec  # noqa: E402
from otoc.pauli_propagation import expectation_z, parse_qasm  # noqa: E402
from otoc.results_io import write_results  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("qasm_folder", type=Path, help="folder with Duke_<circuit>_<q>.qasm files")
    parser.add_argument("circuit", type=str.upper, choices=list(CIRCUITS))
    parser.add_argument("--threshold", type=float, default=1e-5,
                        help="drop Pauli terms below this |coefficient| (0 = exact)")
    parser.add_argument("--output", type=Path, help="default: results/<circuit>_local_pauli.csv")
    args = parser.parse_args()

    spec = get_spec(args.circuit)
    output = args.output or Path("results") / f"{spec.name}_local_pauli.csv"
    values: dict[int, float] = {}

    for qubit in range(spec.num_qubits):
        path = args.qasm_folder / f"{circuit_id(spec.name, qubit)}.qasm"
        if not path.exists():
            logging.warning("missing %s", path)
            continue
        start = time.time()
        values[qubit], terms = expectation_z(parse_qasm(path), qubit, args.threshold)
        logging.info("qubit %2d  <Z> = %+.8f  (%d terms, %.1fs)",
                     qubit, values[qubit], terms, time.time() - start)

    write_results(output, spec.name, spec.num_qubits, values)
    logging.info("Wrote %s", output)


if __name__ == "__main__":
    main()
