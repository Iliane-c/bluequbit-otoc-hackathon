"""Check how an approximate method converges on a few witness qubits.

Before spending credits on a full sweep, run a handful of qubits at increasing
accuracy and look at whether the values stabilise:

    # MPS: does <Z> stop moving when chi doubles?
    python scripts/convergence_test.py G4 --qubits 0 21 37 --device mps.cpu --chi 16 32 64 128

    # Pauli path: compare thresholds on a sample (exact value known) and a graded circuit
    python scripts/convergence_test.py G3 --qubits 35 --device pauli-path --threshold 1e-3 1e-4 1e-5
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.circuits import CIRCUITS, get_spec  # noqa: E402
from otoc.client import connect  # noqa: E402
from otoc.runner import device_options, run_qubits  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("circuit", type=str.upper, choices=list(CIRCUITS))
    parser.add_argument("--qubits", type=int, nargs="+", required=True)
    parser.add_argument("--device", choices=("mps.cpu", "mps.gpu", "pauli-path"), required=True)
    accuracy = parser.add_mutually_exclusive_group(required=True)
    accuracy.add_argument("--chi", type=int, nargs="+", help="bond dimensions to try")
    accuracy.add_argument("--threshold", type=float, nargs="+", help="thresholds to try")
    parser.add_argument("--max-job-minutes", type=float, default=10)
    parser.add_argument("--budget", type=float, default=3.0,
                        help="stop when this many dollars have been spent overall")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    args = parse_args()
    spec = get_spec(args.circuit)
    bq = connect()

    settings = [("chi", c) for c in args.chi] if args.chi else [("threshold", t) for t in args.threshold]
    table: list[tuple[str, dict]] = []
    spent = 0.0

    for knob, level in settings:
        if spent >= args.budget:
            logging.warning("Budget of $%.2f reached, stopping.", args.budget)
            break
        options = device_options(args.device, **{knob: level})
        results = run_qubits(bq, spec.name, spec.num_qubits, args.qubits, args.device, options,
                             max_parallel=len(args.qubits),
                             max_job_seconds=args.max_job_minutes * 60,
                             budget=args.budget - spent, poll_seconds=5)
        spent += sum(r.cost for r in results.values())
        table.append((f"{knob}={level:g}", results))

    print(f"\n{spec.name} on {args.device} (total ${spent:.2f})")
    print(f"{'setting':<18}" + "".join(f"{f'q{q}':>12}" for q in args.qubits))
    for label, results in table:
        cells = "".join(f"{results[q].value:>+12.5f}" if q in results else f"{'-':>12}"
                        for q in args.qubits)
        print(f"{label:<18}{cells}")


if __name__ == "__main__":
    main()
