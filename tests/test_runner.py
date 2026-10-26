"""Test the job scheduler and the CSV helpers with a fake BlueQubit client."""

from types import SimpleNamespace

from otoc.circuits import get_spec, z_observable, distance_to_butterfly
from otoc.results_io import read_results, write_results
from otoc.runner import run_qubits


class FakeClient:
    """Completes each job after ``steps`` status checks; tracks concurrency."""

    def __init__(self, steps=2, fail=(), parallel_limit=None):
        self.steps, self.fail, self.parallel_limit = steps, set(fail), parallel_limit
        self.jobs, self.cancelled, self.max_alive = {}, [], 0

    def _alive(self):
        return sum(j["status"] == "RUNNING" for j in self.jobs.values())

    def run(self, cid, device, pauli_sum, options, asynchronous, job_name):
        if self.parallel_limit and self._alive() >= self.parallel_limit:
            raise RuntimeError("HACKATHON_PARALLEL_JOBS_LIMIT")
        qubit = int(cid.rsplit("_", 1)[1])
        assert pauli_sum[0][0][::-1].index("Z") == qubit  # little-endian observable
        job_id = f"job{len(self.jobs)}"
        self.jobs[job_id] = {"qubit": qubit, "checks": 0, "status": "RUNNING"}
        self.max_alive = max(self.max_alive, self._alive())
        return SimpleNamespace(job_id=job_id)

    def get(self, job_id):
        job = self.jobs[job_id]
        job["checks"] += 1
        if job["status"] == "RUNNING" and job["checks"] >= self.steps:
            job["status"] = "FAILED" if job["qubit"] in self.fail else "COMPLETED"
        return SimpleNamespace(run_status=job["status"], expectation_value=job["qubit"] / 10,
                               cost=0.5, error_message="boom")

    def cancel(self, job_id):
        self.jobs[job_id]["status"] = "CANCELED"
        self.cancelled.append(job_id)


def test_runs_all_qubits_within_parallel_limit():
    bq = FakeClient(parallel_limit=3)
    seen = []
    results = run_qubits(bq, "S2", 16, range(16), "cpu", max_parallel=5, poll_seconds=0,
                         on_result=lambda r: seen.append(r.qubit))
    assert sorted(results) == list(range(16)) == sorted(seen)
    assert results[7].value == 0.7
    assert bq.max_alive <= 3


def test_failed_jobs_are_skipped():
    results = run_qubits(FakeClient(fail={2}), "S1", 4, range(4), "cpu", poll_seconds=0)
    assert sorted(results) == [0, 1, 3]


def test_budget_stops_submissions():
    results = run_qubits(FakeClient(), "S2", 16, range(16), "cpu", max_parallel=1,
                         budget=1.0, poll_seconds=0)
    assert len(results) == 2  # two jobs at $0.50


def test_slow_jobs_are_cancelled():
    bq = FakeClient(steps=10**6)
    results = run_qubits(bq, "S1", 4, [0], "cpu", max_job_seconds=-1, poll_seconds=0)
    assert results == {} and bq.cancelled == ["job0"]


def test_observable_and_layout():
    assert z_observable(4, 0) == "IIIZ"
    assert z_observable(4, 3) == "ZIII"
    g4 = get_spec("g4")
    assert distance_to_butterfly(g4, 0) == 0
    assert distance_to_butterfly(g4, 35) == 10
    assert distance_to_butterfly(g4, 37) == 7  # row 6, column 1


def test_csv_round_trip(tmp_path):
    path = tmp_path / "G1.csv"
    missing = write_results(path, "G1", 3, {0: 0.1, 2: -0.2}, fallback={1: 0.5})
    assert missing == []
    assert read_results(path) == {0: 0.1, 1: 0.5, 2: -0.2}
    assert write_results(path, "G1", 3, {0: 0.1}) == [1, 2]
