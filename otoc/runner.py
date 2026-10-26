"""Job scheduler for running one circuit, qubit by qubit, on BlueQubit.

All the experiments of the hackathon follow the same pattern: submit one job
per qubit, keep a few of them running in parallel (the hackathon allowed at
most 5 concurrent jobs), cancel jobs that take too long, stop before a budget
or a deadline is exceeded, and checkpoint results as they arrive. This module
implements that pattern once.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .circuits import circuit_id, z_observable

log = logging.getLogger(__name__)

ACTIVE_STATUSES = frozenset({"PENDING", "QUEUED", "RUNNING"})
PARALLEL_LIMIT_ERROR = "PARALLEL_JOBS_LIMIT"


@dataclass
class QubitResult:
    """Outcome of the job that measured one qubit."""

    qubit: int
    value: float
    cost: float
    seconds: float


def device_options(device: str, chi: int | None = None,
                   threshold: float | None = None) -> dict:
    """Build the ``options`` dict for ``bq.run`` from the main approximation knobs.

    Args:
        device: BlueQubit device (``cpu``, ``gpu``, ``mps.cpu``, ``mps.gpu``,
            ``pauli-path``).
        chi: MPS bond dimension (MPS devices only).
        threshold: Pauli-path truncation threshold (``pauli-path`` only).
    """
    options: dict = {}
    if device.startswith("mps"):
        if chi is None:
            raise ValueError("MPS devices need a bond dimension (--chi)")
        options["mps_bond_dimension"] = chi
    if device == "pauli-path":
        if threshold is None:
            raise ValueError("pauli-path needs a truncation threshold (--threshold)")
        options["pauli_path_truncation_threshold"] = threshold
    return options


def _cancel_quietly(bq, job_id: str) -> None:
    try:
        bq.cancel(job_id)
    except Exception as exc:  # noqa: BLE001 - best-effort cleanup
        log.debug("could not cancel %s: %s", job_id, exc)


def run_qubits(
    bq,
    circuit: str,
    num_qubits: int,
    qubits: Iterable[int],
    device: str,
    options: dict | None = None,
    *,
    max_parallel: int = 4,
    max_job_seconds: float | None = None,
    deadline: dt.datetime | None = None,
    budget: float | None = None,
    poll_seconds: float = 10.0,
    on_result: Callable[[QubitResult], None] | None = None,
) -> dict[int, QubitResult]:
    """Estimate <Z_q> for each qubit in ``qubits``, in the given order.

    Args:
        bq: BlueQubit client.
        circuit: circuit name, e.g. ``"G3"``.
        num_qubits: number of qubits of the circuit.
        qubits: qubits to run, in submission order.
        device, options: forwarded to ``bq.run``.
        max_parallel: maximum number of jobs alive at the same time.
        max_job_seconds: cancel a job running longer than this.
        deadline: stop submitting and cancel remaining jobs at this time (UTC aware).
        budget: stop submitting new jobs once this many dollars have been spent.
        poll_seconds: delay between two status checks.
        on_result: called after every completed job (used for checkpointing).

    Returns:
        ``{qubit: QubitResult}`` for every job that completed.
    """
    queue = list(qubits)
    total = len(queue)
    active: dict[int, tuple[str, float]] = {}  # qubit -> (job_id, start time)
    results: dict[int, QubitResult] = {}
    spent = 0.0

    def out_of_time() -> bool:
        return deadline is not None and dt.datetime.now(dt.timezone.utc) >= deadline

    def out_of_budget() -> bool:
        return budget is not None and spent >= budget

    try:
        while queue or active:
            if out_of_time():
                log.warning("Deadline reached, stopping.")
                break

            # 1. Collect finished jobs.
            for qubit, (job_id, started) in list(active.items()):
                try:
                    job = bq.get(job_id)
                except Exception as exc:  # noqa: BLE001 - transient API errors
                    log.debug("status check failed for qubit %d: %s", qubit, exc)
                    continue

                elapsed = time.time() - started
                if job.run_status == "COMPLETED":
                    cost = getattr(job, "cost", 0.0) or 0.0
                    spent += cost
                    result = QubitResult(qubit, float(job.expectation_value), cost, elapsed)
                    results[qubit] = result
                    del active[qubit]
                    log.info("qubit %2d  <Z> = %+.6f  cost $%.3f  %5.0fs  [%d done, $%.2f spent]",
                             qubit, result.value, cost, elapsed, len(results), spent)
                    if on_result:
                        on_result(result)
                elif job.run_status not in ACTIVE_STATUSES:
                    del active[qubit]
                    log.error("qubit %d failed with status %s: %s", qubit, job.run_status,
                              getattr(job, "error_message", ""))
                elif max_job_seconds and elapsed > max_job_seconds:
                    _cancel_quietly(bq, job_id)
                    del active[qubit]
                    log.warning("qubit %d cancelled after %.0fs", qubit, elapsed)

            # 2. Fill the free slots.
            while queue and len(active) < max_parallel and not out_of_budget():
                qubit = queue[0]
                try:
                    job = bq.run(
                        circuit_id(circuit, qubit),
                        device=device,
                        pauli_sum=[(z_observable(num_qubits, qubit), 1.0)],
                        options=options or None,
                        asynchronous=True,
                        job_name=f"{circuit}_{qubit}_{device}",
                    )
                except Exception as exc:  # noqa: BLE001
                    if PARALLEL_LIMIT_ERROR in str(exc):
                        break  # platform is full: retry on the next poll
                    log.error("could not submit qubit %d: %s", qubit, str(exc)[:200])
                    queue.pop(0)
                    continue
                queue.pop(0)
                active[qubit] = (job.job_id, time.time())
                log.info("submitted qubit %d (job %s)", qubit, job.job_id)

            if out_of_budget() and queue:
                log.warning("Budget of $%.2f reached, %d qubits not submitted.", budget, len(queue))
                queue.clear()

            if queue or active:
                time.sleep(poll_seconds)
    finally:
        # Never leave paid jobs running behind us (deadline, Ctrl+C, crash).
        for qubit, (job_id, _) in active.items():
            log.warning("cancelling unfinished job for qubit %d", qubit)
            _cancel_quietly(bq, job_id)

    log.info("Finished: %d/%d qubits completed, $%.2f spent.", len(results), total, spent)
    return results
