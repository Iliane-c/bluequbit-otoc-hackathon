"""Cancel every BlueQubit job that is still pending or running.

Useful after an interrupted run, so that orphaned jobs stop consuming credits.

    python scripts/cancel_jobs.py --dry-run   # list only
    python scripts/cancel_jobs.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from otoc.client import connect  # noqa: E402
from otoc.runner import ACTIVE_STATUSES  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="list the jobs without cancelling")
    args = parser.parse_args()

    bq = connect()
    # bq.search() without a filter is more robust than one call per status.
    active = [job for job in (bq.search() or []) if job.run_status in ACTIVE_STATUSES]
    if not active:
        print("No pending or running jobs.")
        return

    for job in active:
        cost = getattr(job, "estimated_cost", 0.0) or 0.0
        print(f"{job.job_id}  {job.device:<10}  {job.run_status:<8}  est. ${cost:.2f}")
        if not args.dry_run:
            bq.cancel(job.job_id)
    print(f"{len(active)} job(s) {'found' if args.dry_run else 'cancelled'}.")


if __name__ == "__main__":
    main()
