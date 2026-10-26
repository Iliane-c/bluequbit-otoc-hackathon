"""Print a circuit's size and BlueQubit's cost/runtime estimates (both free).

    python scripts/inspect_circuit.py G1 --devices cpu gpu
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.circuits import CIRCUITS, circuit_id, get_spec  # noqa: E402
from otoc.client import connect  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("circuit", type=str.upper, choices=list(CIRCUITS))
    parser.add_argument("--qubit", type=int, default=0, help="which program to inspect")
    parser.add_argument("--devices", nargs="+", default=["cpu", "gpu"])
    args = parser.parse_args()

    spec = get_spec(args.circuit)
    cid = circuit_id(spec.name, args.qubit)
    bq = connect()

    print(f"{cid}: {spec.description}")
    print(bq.get_circuit_info(cid))
    for device in args.devices:
        try:
            estimate = bq.estimate(cid, device=device)
        except Exception as exc:  # noqa: BLE001
            print(f"{device:>10}: estimate failed ({exc})")
            continue
        warning = f"  warning: {estimate.warning_message}" if estimate.warning_message else ""
        print(f"{device:>10}: ~{estimate.estimated_runtime} ms, "
              f"~${estimate.estimated_cost}{warning}")


if __name__ == "__main__":
    main()
