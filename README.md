# Simulating Quantum Echoes Classically

### OTOC estimation on 30–38-qubit circuits: BlueQubit × DuQuantum 2026 hackathon

In 2025, Google reported a *verifiable* quantum advantage. Its Willow chip measured how
information scrambles through a 65-qubit circuit, about 13,000× faster than the best known
classical method on the Frontier supercomputer. This hackathon asked the opposite question:
**how far can classical simulation go on the same kind of measurement?**

This repository contains my code, results and experiment log for that 24-hour challenge
(Duke University and online, October 24–25, 2026). We were given seven circuits with 4 to 38
qubits and had to estimate one OTOC-type quantity per qubit, 190 numbers in total, using
exact, tensor-network and Pauli-propagation simulators.

---

## Contents

1. [Background: what is an OTOC?](#1-background-what-is-an-otoc)
2. [Why OTOCs matter](#2-why-otocs-matter)
3. [Why OTOCs are hard to simulate classically](#3-why-otocs-are-hard-to-simulate-classically)
4. [The challenge](#4-the-challenge)
5. [Classical toolbox](#5-classical-toolbox)
6. [What I did, circuit by circuit](#6-what-i-did-circuit-by-circuit)
7. [Findings](#7-findings)
8. [Repository layout](#8-repository-layout)
9. [Getting started](#9-getting-started)
10. [Further reading](#10-further-reading)

---

## 1. Background: what is an OTOC?

### The butterfly effect, quantum version

In a classical chaotic system, a tiny change in the initial conditions grows exponentially
with time. This is the butterfly effect. Quantum mechanics has no trajectories to compare, so
the question has to be asked differently:

> If I disturb one qubit now, how quickly, and how far, does that disturbance spread through
> the rest of the system?

This spreading is called **information scrambling**. Information that starts on one qubit ends
up hidden in complicated correlations among many qubits. No local measurement can recover it,
yet the evolution is still unitary, so nothing is lost.

### The out-of-time-order correlator

Take two operators, each acting on a single qubit:

- $B$, the **butterfly**, is the perturbation, for example a Pauli on qubit $b$;
- $M$ is the **measurement**, for example $Z$ on qubit $q$.

Evolve the butterfly in the Heisenberg picture through the circuit $U$:
$B(t) = U^\dagger B\, U$. At $t = 0$, $B$ and $M$ act on different qubits and commute. As the
circuit runs, $B(t)$ grows into a sum of longer and longer Pauli strings. Once its support
reaches qubit $q$, it stops commuting with $M$.

The OTOC measures this loss of commutativity:

$$
C(t) \;=\; \langle\, B(t)^\dagger\, M^\dagger\, B(t)\, M \,\rangle ,
\qquad
\operatorname{Re} C(t) \;=\; 1 - \tfrac12\,\big\langle\, |[B(t), M]|^2 \,\big\rangle
\quad\text{(for Pauli } B, M\text{)} .
$$

- **$C \approx 1$**: the perturbation has not reached qubit $q$ yet. The qubit lies outside the
  butterfly's light cone.
- **$C \to 0$**: the perturbation has fully scrambled into the region around $q$.

The front where $C$ starts to drop moves outward from the butterfly at a finite speed, the
**butterfly velocity**. Plotting $C$ for every qubit therefore gives a map of how the
perturbation spreads through the device.

### Why "out of time order"?

Write the correlator out in full: $U^\dagger B^\dagger U\, M^\dagger\, U^\dagger B U\, M$. The
time arguments alternate $t, 0, t, 0$, so the system is not probed in chronological order. An
ordinary experiment that only moves forward in time cannot measure this directly. It needs
**time reversal**: run the circuit forward, perturb, run it backward.

### The echo protocol

On a quantum computer, running backward is easy: apply $U^\dagger$. This gives a
**Loschmidt echo**:

```
|0…0⟩ ──[ U ]──[ B on butterfly qubit ]──[ U† ]──  …  ── measure ⟨Z_q⟩
          forward       perturbation          backward
```

Without the butterfly, $U^\dagger U = I$ and the state returns exactly to where it started: a
perfect echo. With the butterfly, the echo is only perfect on qubits the perturbation never
reached. Everywhere else it is degraded by exactly the amount of scrambling.

Google's 2025 experiment, and this challenge, use a **second-order OTOC**, written
$\text{OTOC}^{(2)}$. The forward–backward loop is applied twice, so each circuit applies $U$ or
$U^\dagger$ **four times**. This higher-order echo is more sensitive to the interference effects
discussed in section 3.

---

## 2. Why OTOCs matter

- **Quantum chaos and black holes.** OTOCs were introduced in superconductivity theory (Larkin
  & Ovchinnikov, 1969). They came back as the standard diagnostic of quantum chaos when black
  holes were shown to be the fastest possible scramblers. Their decay rate obeys a universal
  bound: Maldacena, Shenker and Stanford's "bound on chaos".
- **A verifiable quantum advantage.** Random-circuit sampling produces bitstrings that nobody
  can check. An OTOC is an *expectation value*, a physical quantity that another quantum
  computer, or nature itself, can reproduce. Google's *Quantum Echoes* experiment measured
  $\text{OTOC}^{(2)}$ on 65 qubits of the Willow chip in about 2 hours per dataset. It estimated
  that the same data would take about 3 years on Frontier, a speedup of about 13,000×.
- **Learning about real systems.** The same echo can probe interactions in physical systems.
  Google applied it to NMR data on nuclear spins, as a "longer molecular ruler" for measuring
  distances inside molecules. That demonstration was still within classical reach.
- **Benchmarking hardware and algorithms.** An echo returns exactly to the initial state in
  the noiseless, unperturbed case. Any deviation measures noise or scrambling, which makes OTOCs
  a sharp test for quantum processors and for the classical simulators that claim to match
  them.

## 3. Why OTOCs are hard to simulate classically

In the Heisenberg picture, the measured operator is a sum over **Pauli paths**: the ways a
Pauli string can branch through every gate of the circuit. The number of paths grows
exponentially. A second-order echo adds a further difficulty. The final value comes from the
**constructive interference of many small contributions**, which only add up when their phases
align, so it is not dominated by a few large terms.

This is bad news for the standard approximations:

- **Truncation.** Dropping small Pauli terms removes exactly the many weak paths that interfere
  constructively.
- **Matrix product states.** An MPS only works if the entanglement stays low. Scrambling is,
  by definition, the growth of entanglement, and on a 2D grid the bond dimension needed grows
  quickly.
- **Exact state vectors.** These need $2^n$ amplitudes: about 16 GB of memory at 30 qubits, and
  far more at 36–38 qubits.

What remains tractable depends on the **structure** of the circuit:

- whether it is a 1D chain or a 2D grid;
- whether its gates are Clifford or Haar-random;
- how far each qubit sits from the butterfly.

Finding that structure was the core of the challenge.

---

## 4. The challenge

Each circuit comes with one program per qubit, `Duke_<circuit>_<q>`. The program is the
$\text{OTOC}^{(2)}$ echo with the measurement on qubit $q$. For each program we estimate
**⟨Z_q⟩**, starting from |0…0⟩.

| Circuit | Qubits | Layout | 2-qubit gates | Layers in U | Butterfly | CZ count | Points |
|---|---|---|---|---|---|---|---|
| S1 | 4 | 1D chain | Haar-random | 4 | 0 (end) | 72 | 100 |
| S2 | 16 | 1D chain | Haar-random | 12 | 0 (end) | 1,080 | 100 |
| S3 | 30 | 5×6 grid | random Clifford + Rz | 16 | 14 | 1,568 | 100 |
| G1 | 30 | 1D chain | Haar-random | 32 | 0 (end) | 5,568 | 300 |
| G2 | 36 | 1D chain | Haar-random | 18 | 18 (middle) | 3,780 | 600 |
| G3 | 36 | 6×6 grid | random Clifford + Rz | 24 | 14 | 2,872 | 800 |
| G4 | 38 | 6×6 grid + 2 | Haar-random | 16 | 0 (corner) | 3,024 | 1,000 |

The rules:

- **Scoring.** Each circuit scores **corr² × points**, using the Pearson correlation with the
  exact values over that circuit's qubits.
- **What the score rewards.** Scale and offset are ignored, so only the *shape* of the
  scrambling profile matters. The sign does matter: a negative correlation, or all-equal values,
  score 0.
- **Access.** S1–S3 come with their QASM source. G1–G4 are hidden and can only be run by ID on
  BlueQubit's cloud simulators.

## 5. Classical toolbox

BlueQubit gives access to three families of simulators. Each one exploits a different kind of
structure.

| Method | Device | What it exploits | Accuracy knob | Cost grows with | Best here for |
|---|---|---|---|---|---|
| **State vector** | `cpu`, `gpu` | nothing; exact | none | $2^n$ | ≤ 30–34 qubits (S1–S3, G1) |
| **Matrix product state** | `mps.cpu`, `mps.gpu` | low entanglement, 1D geometry | bond dimension χ | ~χ³ per gate | 1D chains (G2) |
| **Pauli-path propagation** | `pauli-path` | Clifford gates (one Pauli string maps to one) | truncation threshold δ | number of paths $N_P(\delta) \propto \delta^{-\alpha}$ | Clifford grids (G3) |

How each method works:

- **State vector** stores all $2^n$ amplitudes and applies gates exactly.
- **MPS** writes the state as a chain of tensors and truncates the bond dimension to χ. The
  error stays controlled as long as the entanglement across every cut of the chain is small.
- **Pauli propagation** evolves the observable $Z_q$ backward through the circuit as a weighted
  sum of Pauli strings, and drops terms with $|c| < \delta$. A Clifford gate maps one Pauli
  string to exactly one other, so Clifford-heavy circuits stay compact. Every non-Clifford
  rotation can split a term in three. The final value is the sum of the coefficients of the
  strings made only of $I$ and $Z$. I also wrote my own implementation for the open sample
  circuits, [`otoc/pauli_propagation.py`](otoc/pauli_propagation.py), and tested it against
  exact state vectors.

A recent BlueQubit benchmark, [Mazumder et al., arXiv:2607.09882](https://arxiv.org/abs/2607.09882),
measures these trade-offs across platforms. Three results bear on this challenge:

- **MPS on GPU.** Runtime grows as $\chi^{1.49}$ on GPU and $\chi^{2.03}$ on CPU, so the GPU
  advantage grows with the bond dimension. On low-entanglement circuits, kernel-launch overhead
  makes the GPU slower instead.
- **Pauli paths on GPU.** On IBM's 127-qubit kicked-Ising circuit, Pauli propagation on GPU is
  up to ~1,700× faster at fine thresholds (δ = 2.5 × 10⁻⁵). It is the only backend tested that
  reaches the δ < 10⁻⁵ regime.
- **Error is not monotone in δ.** The approximation error peaks at an intermediate threshold,
  so a coarse δ can look converged when it is not.

These results explain the main limitation I hit: on CPU, Pauli paths at δ = 10⁻⁴ either ran
out of time near the butterfly or truncated everything (section 7).

---

## 6. What I did, circuit by circuit

The full chronological log, 31 scripts, is in [`experiments/`](experiments/README.md).

| Circuit | Method submitted | Reasoning |
|---|---|---|
| S1, S3 | exact state vector, CPU | Small enough for exact simulation. S3 also served as ground truth for my Pauli-propagation code. |
| G1 | exact state vector, GPU | 30 qubits but depth 384: GPU, with all 30 jobs submitted asynchronously. |
| G2 | MPS, χ = 16 | 1D chain with the butterfly in the middle: the natural MPS setting. I measured the cost of one job at χ = 8…64 first. |
| G3 | MPS, with Pauli path (δ = 10⁻⁴) where available | Clifford grid: Pauli paths are accurate, but slow near the butterfly. I scheduled qubits from far to near and kept MPS for the rest. |
| G4 | MPS, χ = 32 (χ = 64 on witness qubits) | Haar-random 2D grid: the hardest case. No method converged within the budget. |

## 7. Findings

1. **Test convergence on a few witness qubits before paying for a full sweep.** On G4,
   qubit 0 gave 0.270 at χ = 32 and 0.098 at χ = 64: the MPS was far from converged on a
   scrambling 2D circuit. Similar tests on G2 and G3 set the bond dimension and the threshold.
2. **The two approximations disagree.** On G3 qubit 0, MPS gave −0.275 and Pauli path gave
   −0.015. On a Clifford grid the Pauli-path value is the more trustworthy of the two.
3. **A threshold that is too coarse returns zeros.** On G4 at δ = 10⁻⁴, every completed grid
   qubit returned exactly 0, because all paths were truncated. All-equal values score 0, so
   this run was worse than useless. Its noise is not a smooth function of δ either, in line with
   the non-monotone error reported by Mazumder et al.
4. **Distance to the butterfly sets the cost.** Qubits outside the light cone are cheap, and
   their echo is nearly perfect (G2 end qubits: ⟨Z⟩ ≈ 0.9997). Qubits next to the butterfly
   are the expensive ones. Scheduling far qubits first means a deadline cuts off the expensive
   jobs rather than the easy ones.
5. **Infrastructure matters as much as physics.** Much of the 24 hours went into job
   orchestration: asynchronous submission, a 5-job parallel limit, timeouts, budget caps,
   checkpointing and cancelling orphan jobs. That logic now lives in one place:
   [`otoc/runner.py`](otoc/runner.py).

**With more time,** I would rerun G3 and G4 on the GPU backends (`mps.gpu`, GPU Pauli paths)
at finer δ and larger χ. Mazumder et al. show that this is exactly where GPUs pull ahead.

---

## 8. Repository layout

The repository has two parts:

- **`experiments/`** is the record of the hackathon: what was tried, what failed and what was
  kept, by circuit and in chronological order.
- **`otoc/` and `scripts/`** are what that work turned into: one tested package and a few
  command-line tools that reproduce every run.

```
experiments/               hackathon log: 31 scripts in chronological order
  00_setup/  01_samples/  02_G1/  03_G2/  04_G3/  05_G4/
otoc/                      Python package
  circuits.py              circuit metadata, IDs, Z observables, distance to the butterfly
  client.py                BlueQubit client from .env
  runner.py                parallel job scheduler (limits, timeouts, budget, deadline)
  results_io.py            read/write submission CSVs
  pauli_propagation.py     local Pauli-propagation simulator for QASM files
scripts/
  check_setup.py           verify the API token
  inspect_circuit.py       circuit info and cost/runtime estimates (free)
  run_circuit.py           full sweep on any device, with checkpointing and --resume
  convergence_test.py      accuracy sweep (χ or δ) on witness qubits
  simulate_local.py        local simulation of the sample QASM files
  combine_results.py       merge or negate result files
  cancel_jobs.py           cancel orphaned jobs
tests/                     unit tests (fake client, exact state-vector reference)
results/                   submitted CSV files
```

## 9. Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then paste your BlueQubit API token
python scripts/check_setup.py
python -m pytest                # offline tests, no credits used
```

### Reproducing the runs

```bash
# Exact simulation
python scripts/run_circuit.py S1 --device cpu
python scripts/run_circuit.py G1 --device gpu

# Local Pauli propagation on the sample QASM files (free)
python scripts/simulate_local.py qasm/S3 S3 --threshold 1e-5

# G2: choose chi on the butterfly qubit, then sweep
python scripts/convergence_test.py G2 --qubits 18 --device mps.cpu --chi 8 16 32 64
python scripts/run_circuit.py G2 --device mps.cpu --chi 16 --budget 2

# G3: MPS baseline, Pauli-path refinement (far qubits first), then merge
python scripts/run_circuit.py G3 --device mps.cpu --chi 32 --output results/G3_mps.csv
python scripts/run_circuit.py G3 --device pauli-path --threshold 1e-4 --order far-first \
    --max-parallel 4 --max-job-minutes 9 --output results/G3_pauli_path_1e-4_partial.csv
python scripts/combine_results.py results/G3_mps.csv \
    --override results/G3_pauli_path_1e-4_partial.csv --qubits 0 1 3 4 30 31 \
    -o results/G3_mps_plus_pauli_path.csv

# G4: convergence check, chi=32 sweep, then refine the largest values at chi=64
python scripts/convergence_test.py G4 --qubits 0 21 37 --device mps.cpu --chi 16 32 64
python scripts/run_circuit.py G4 --device mps.cpu --chi 32 --max-parallel 3
python scripts/run_circuit.py G4 --device mps.cpu --chi 64 --top-k 24 \
    --fallback results/G4_mps_chi32.csv --output results/G4_mps_chi32_chi64_mix.csv
```

Interrupted runs continue where they stopped with `--resume`. If a script crashes,
`python scripts/cancel_jobs.py` cancels any jobs left running, so that they stop using
credits.

### Results

The files in `results/` are the CSVs submitted during the hackathon.

| File | Method |
|---|---|
| `S1_exact_cpu.csv`, `S3_exact_cpu.csv` | exact, CPU |
| `G1_exact_gpu.csv` | exact, GPU |
| `G2_mps_chi16.csv` | MPS, χ = 16 |
| `G3_mps.csv` | MPS (mps.cpu) |
| `G3_pauli_path_1e-4_partial.csv` | Pauli path δ = 10⁻⁴, unfinished qubits set to 0 |
| `G3_mps_plus_pauli_path.csv` | MPS, with Pauli-path values for qubits 0, 1, 3, 4, 30, 31 |
| `G4_mps_chi32.csv` | MPS, χ = 32 |
| `G4_mps_chi32_chi64_mix.csv` | χ = 32, with χ = 64 values for qubits 0, 21, 37 |
| `G4_*_negated.csv` | same values with flipped sign (sign check) |
| `G4_pauli_path_1e-4.csv` | Pauli path δ = 10⁻⁴ (degenerate: almost all zeros) |

---

## 10. Further reading

**The experiment this challenge is based on**
- Google Quantum AI, *Observation of constructive interference at the edge of quantum
  ergodicity*, Nature (2025). [doi:10.1038/s41586-025-09526-6](https://www.nature.com/articles/s41586-025-09526-6)
- X. Mi et al. (Google Quantum AI), *Information scrambling in quantum circuits*, Science 374,
  1479 (2021). An earlier OTOC experiment on Sycamore.

**OTOCs and scrambling**
- A. I. Larkin & Y. N. Ovchinnikov, *Quasiclassical method in the theory of superconductivity*,
  JETP 28, 1200 (1969). The first appearance of the OTOC.
- S. H. Shenker & D. Stanford, *Black holes and the butterfly effect*,
  [arXiv:1306.0622](https://arxiv.org/abs/1306.0622).
- J. Maldacena, S. H. Shenker & D. Stanford, *A bound on chaos*,
  [arXiv:1503.01409](https://arxiv.org/abs/1503.01409).
- B. Swingle, G. Bentsen, M. Schleier-Smith & P. Hayden, *Measuring the scrambling of quantum
  information*, [arXiv:1602.06271](https://arxiv.org/abs/1602.06271). Proposes the echo protocol.

**Classical simulators**
- A. R. Mazumder et al. (BlueQubit), *Benchmarking Zero-Setup Quantum Circuit Simulators*,
  [arXiv:2607.09882](https://arxiv.org/abs/2607.09882). Code:
  [github.com/arulrhikm/mps-pps-zero-setup-benchmarks](https://github.com/arulrhikm/mps-pps-zero-setup-benchmarks).
- BlueQubit, *Pauli path simulators for benchmarking quantum utility claims*,
  [bluequbit.io/blog/pauli-path-simulators](https://www.bluequbit.io/blog/pauli-path-simulators).

## Acknowledgements

The challenge, circuits and simulators were provided by [BlueQubit](https://www.bluequbit.io),
in collaboration with DuQuantum 2026 at Duke University.
