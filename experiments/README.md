# Experiments log

These are the scripts I actually wrote and ran during the 24-hour hackathon, in
chronological order. They show how the approach evolved, circuit by circuit:
what was tried, what failed and what was kept. The final, reusable tools that
came out of this work are in [`../otoc`](../otoc) and [`../scripts`](../scripts).

The scripts are kept close to their original form. Their comments and messages
are now in English, and each one starts with a docstring explaining its purpose
and naming its original file. Every script is standalone:

- it reads `BLUEQUBIT_API_TOKEN` from `.env`;
- it writes its CSV to the current directory;
- most of them spend BlueQubit credits.

## 00 Setup

| Script | Purpose |
|---|---|
| `01_check_setup.py` | Check that the token is set and the SDK connects |
| `02_qft_smoke_test.py` | Run a 5-qubit QFT to test the SDK before the challenge opened |
| `03_cancel_all.py` | Cancel stray jobs that kept running (and billing) after a script stopped |
| `04_cancel_all_safe.py` | Same, working around an SDK crash in `search(run_status=...)` |

## 01 Samples (S1–S3, open circuits)

| Script | Purpose |
|---|---|
| `01_s1_run_by_id.py` | First end-to-end submission: S1 by ID, exact CPU |
| `02_s3_run_by_id.py` | S3 (30 qubits), exact CPU, used as ground truth |
| `03_local_pauli_propagation.py` | My own Pauli-propagation simulator on the QASM files, checked against S3 |

## 02 G1 (30 qubits, deep 1D chain): exact

| Script | Purpose |
|---|---|
| `01_g1_inspect_and_estimate.py` | Free circuit info and cost estimate, CPU vs GPU |
| `02_g1_exact_gpu_async.py` | All 30 jobs submitted asynchronously on GPU |
| `03_g1_fill_missing.py` | Recompute the 2 qubits that failed |

## 03 G2 (36 qubits, 1D chain): MPS

| Script | Purpose |
|---|---|
| `01_g2_mps_chi2_chi4_free_tier.py` | Free-tier only: chi=2 then chi=4, compare the two passes |
| `02_g2_single_job_cost.py` | Real cost and runtime of one job at chi = 8, 16, 32, 64 |
| `03_g2_mps_chi8_budget_loop.py` | Full sweep at chi=8, tracking the real cost |
| `04_g2_mps_chi16_full.py` | **Submitted:** full sweep at chi=16 |

## 04 G3 (36 qubits, Clifford grid): MPS and Pauli path

| Script | Purpose |
|---|---|
| `01_g3_pauli_path_threshold_sweep.py` | Pauli path at 1e-3 then 1e-4: too slow and expensive in sequence |
| `02_g3_mps_chi32.py` | MPS chi=32 as a complete fallback |
| `03_g3_mps_chi32_retry.py` | Same, with retries after timeouts |
| `04_g3_pauli_path_calibrated.py` | Calibrate on the butterfly qubit, choose the threshold from the projected cost |
| `05_g3_mps_chi64_cost_guard.py` | MPS chi=64, cancelling any job whose estimate is too high |
| `06_g3_mps_chi32_free.py` | MPS chi=32, uncapped (free tier) |
| `07_g3_pauli_path_async.py` | Pauli path, asynchronous with 2 parallel jobs and an 8-minute timeout |
| `08_g3_threshold_benchmark.py` | Thresholds 1e-3 / 1e-4 / 1e-5 on S3 (known answer) and G3 |
| `09_g3_pauli_path_far_first.py` | Pauli path 1e-4, far-from-butterfly qubits first, until a deadline |
| `10_g3_merge_mps_pauli_path.py` | **Submitted:** MPS values, replaced by Pauli path where it finished |

## 05 G4 (38 qubits, Haar-random grid): MPS

| Script | Purpose |
|---|---|
| `01_g4_mps_convergence.py` | chi = 16…128 on 3 witness qubits: not converged (q0: 0.270 at chi=32, 0.098 at chi=64) |
| `02_g4_mps_chi32_parallel.py` | **Submitted:** complete chi=32 baseline with a thread pool |
| `03_g4_mps_chi64_top_qubits.py` | Refine the 24 largest values at chi=64 under a $35 cap |
| `04_g4_mps_chi64_rescue.py` | Recover the orphan jobs of the previous run and continue |
| `05_g4_pauli_path_q0_1e-5.py` | Pauli path on the butterfly qubit, threshold 1e-5: too slow |
| `06_g4_pauli_path_q0_1e-4.py` | Same at 1e-4 |
| `07_g4_pauli_path_full_1e-4.py` | Full sweep at 1e-4: grid qubits return exactly 0, so the result is unusable |

## What I learned

1. **Exact simulation whenever it fits.** Up to 30 qubits, CPU or GPU gives exact values,
   which is the best possible score.
2. **Measure before sweeping.** One job on the hardest qubit gives the cost and the accuracy
   (`02_g2_single_job_cost.py`, `04_g3_pauli_path_calibrated.py`,
   `01_g4_mps_convergence.py`).
3. **Match the method to the structure.** MPS works for 1D chains (G2). Pauli paths work for
   Clifford-heavy circuits (G3). Neither converges on G4's Haar-random 2D grid.
4. **Infrastructure matters as much as physics.** Asynchronous submission, the parallel-jobs
   limit, timeouts, budget caps, checkpointing and cancelling orphan jobs took a large share
   of the 24 hours. This is what `otoc/runner.py` now does in one place.
