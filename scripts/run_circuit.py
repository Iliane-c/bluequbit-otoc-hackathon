"""Estimate <Z_q> for every qubit of a challenge circuit on BlueQubit.

This single script replaces the per-circuit scripts used during the hackathon.
The approximation method is chosen with --device and its accuracy knob:

    # Exact state vector (small circuits: S1-S3 on CPU, G1 on GPU)
    python scripts/run_circuit.py S1 --device cpu
    python scripts/run_circuit.py G1 --device gpu

    # Matrix product state with bond dimension chi (1D chains: G2)
    python scripts/run_circuit.py G2 --device mps.cpu --chi 16

    # Pauli-path propagation (Clifford-heavy grids: G3), easy qubits first
    python scripts/run_circuit.py G3 --device pauli-path --threshold 1e-4 \
        --order far-first --max-parallel 4 --max-job-minutes 9

    # Refine only the 24 largest values of a previous run, keep the others
    python scripts/run_circuit.py G4 --device mps.cpu --chi 64 \
        --fallback results/G4_mps_chi32.csv --top-k 24

Results are checkpointed to the output CSV after every completed job, so the
file is always a valid submission even if the run is interrupted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.circuits import CIRCUITS, distance_to_butterfly, get_spec  # noqa: E402
from otoc.client import connect  # noqa: E402
from otoc.results_io import read_results, write_results  # noqa: E402
from otoc.runner import device_options, run_qubits  # noqa: E402

DEVICES = ("cpu", "gpu", "mps.cpu", "mps.gpu", "pauli-path")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("circuit", type=str.upper, choices=list(CIRCUITS))
    parser.add_argument("--device", choices=DEVICES, default="cpu")
    parser.add_argument("--chi", type=int, help="MPS bond dimension")
    parser.add_argument("--threshold", type=float, help="Pauli-path truncation threshold")
    parser.add_argument("--qubits", type=int, nargs="+",
                        help="only run these qubits (default: all)")
    parser.add_argument("--order", choices=("index", "far-first", "near-first"), default="index",
                        help="submission order; far-first runs the cheap qubits "
                             "(far from the butterfly) before the expensive ones")
    parser.add_argument("--fallback", type=Path,
                        help="previous result CSV used for qubits that are not (re)computed")
    parser.add_argument("--top-k", type=int,
                        help="with --fallback: only recompute the K qubits with the largest |value|")
    parser.add_argument("--resume", action="store_true",
                        help="skip qubits already present in the output file")
    parser.add_argument("--max-parallel", type=int, default=4,
                        help="concurrent jobs (the hackathon limit was 5)")
    parser.add_argument("--max-job-minutes", type=float, help="cancel jobs running longer")
    parser.add_argument("--budget", type=float, help="stop submitting after spending this ($)")
    parser.add_argument("--deadline", type=dt.datetime.fromisoformat,
                        help="ISO time to stop at, e.g. 2026-10-25T15:15+00:00")
    parser.add_argument("--output", type=Path, help="output CSV (default: results/<name>.csv)")
    return parser.parse_args()


def default_output(args: argparse.Namespace) -> Path:
    tag = args.device.replace(".", "_").replace("-", "_")
    if args.chi:
        tag += f"_chi{args.chi}"
    if args.threshold:
        tag += f"_{args.threshold:g}"
    return Path("results") / f"{args.circuit}_{tag}.csv"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    args = parse_args()
    spec = get_spec(args.circuit)
    output = args.output or default_output(args)
    options = device_options(args.device, chi=args.chi, threshold=args.threshold)

    fallback = read_results(args.fallback) if args.fallback else {}
    values: dict[int, float] = read_results(output) if args.resume and output.exists() else {}

    # Select and order the qubits to run.
    qubits = args.qubits or list(range(spec.num_qubits))
    if args.top_k:
        if not fallback:
            sys.exit("--top-k needs --fallback")
        qubits = sorted(qubits, key=lambda q: -abs(fallback.get(q, 0.0)))[:args.top_k]
    if args.order == "far-first":
        qubits.sort(key=lambda q: -distance_to_butterfly(spec, q))
    elif args.order == "near-first":
        qubits.sort(key=lambda q: distance_to_butterfly(spec, q))
    qubits = [q for q in qubits if q not in values]

    logging.info("%s (%d qubits, %d pts): running %d qubits on %s %s -> %s",
                 spec.name, spec.num_qubits, spec.points, len(qubits), args.device,
                 options or "", output)

    def checkpoint(result) -> None:
        values[result.qubit] = result.value
        write_results(output, spec.name, spec.num_qubits, values, fallback, warn=False)

    run_qubits(
        connect(), spec.name, spec.num_qubits, qubits, args.device, options,
        max_parallel=args.max_parallel,
        max_job_seconds=args.max_job_minutes * 60 if args.max_job_minutes else None,
        deadline=args.deadline,
        budget=args.budget,
        on_result=checkpoint,
    )

    missing = write_results(output, spec.name, spec.num_qubits, values, fallback)
    if missing:
        logging.warning("Rerun with --resume to complete the missing qubits.")
    logging.info("Wrote %s", output)


if __name__ == "__main__":
    main()
