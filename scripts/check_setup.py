"""Check that the BlueQubit token is configured and the API is reachable.

    python scripts/check_setup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.client import connect  # noqa: E402


def main() -> None:
    try:
        bq = connect()
        info = bq.get_circuit_info("Duke_S1_0")  # free call that needs a valid token
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Setup failed: {exc}")
    print(f"OK: connected to BlueQubit, Duke_S1_0 has {info.num_qubits} qubits.")


if __name__ == "__main__":
    main()
