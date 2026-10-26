"""Combine or transform submission files.

    # Replace some MPS values by more accurate Pauli-path values
    python scripts/combine_results.py results/G3_mps.csv \
        --override results/G3_pauli_path_1e-4_partial.csv --qubits 0 1 3 4 30 31 \
        --output results/G3_mps_plus_pauli_path.csv

    # Take every non-zero value of a partially completed run
    python scripts/combine_results.py base.csv --override partial.csv --skip-zeros -o out.csv

    # Flip the sign of every value (a negative correlation scores 0)
    python scripts/combine_results.py results/G4_mps_chi32.csv --negate -o neg.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.results_io import read_results, write_results  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base", type=Path, help="base submission CSV")
    parser.add_argument("--override", type=Path, help="CSV whose values replace the base ones")
    parser.add_argument("--qubits", type=int, nargs="+", help="only override these qubits")
    parser.add_argument("--skip-zeros", action="store_true",
                        help="ignore override values that are exactly 0 (placeholders)")
    parser.add_argument("--negate", action="store_true", help="flip the sign of every value")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    circuit = args.base.read_text().split("Duke_", 1)[1].split("_", 1)[0]
    values = read_results(args.base)

    if args.override:
        for qubit, value in read_results(args.override).items():
            if args.qubits and qubit not in args.qubits:
                continue
            if args.skip_zeros and value == 0.0:
                continue
            values[qubit] = value
            print(f"qubit {qubit}: overridden with {value:+.6f}")

    if args.negate:
        values = {q: -v if v else 0.0 for q, v in values.items()}

    write_results(args.output, circuit, len(values), values)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
