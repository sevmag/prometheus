# Injecting τ (ν_τ) events in Prometheus

How to inject ν_τ charged-current events, propagate the τ, and record its
decay light (the classic **double-bang**) with the GPU PPC backend on the FASRC
cluster. Driver: `examples/run_prometheus_sim.py`.

```bash
# Cluster install (adjust to yours)
PROM_ROOT=/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus
SPACK_ROOT=/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/spack
```

## 1. Environment (every session)

```bash
source $SPACK_ROOT/share/spack/setup-env.sh
spack env activate prometheus
module load cuda/12.4.1-fasrc01     # libcudart for the GPU ppc, at build AND runtime
cd $PROM_ROOT
```

## 2. Injecting a τ — the channel

A ν_τ CC interaction is selected by the two final states:

```
--final_1 TauMinus --final_2 Hadrons     # ν_τ CC  → τ⁻ + hadronic recoil
```

| Channel | `--final_1 / --final_2` |
|---|---|
| ν_τ CC | `TauMinus` / `Hadrons` |
| ν̄_τ CC | `TauPlus` / `Hadrons` |
| ν_μ CC | `MuMinus` / `Hadrons` |
| ν_e / NC (cascade) | `NuEBar` / `Hadrons` |

Other knobs:
- **Energy:** `--emin` / `--emax` (GeV). **`--emin` must be strictly `< --emax`**
  (equal values raise `injection minimal energy must be < maximal energy`); for
  "10 PeV" use e.g. `--emin 9.9e6 --emax 1.01e7`.
- **Injection volume** is the default; add `--ranged` only for a ranged injection
  (do *not* for the examples below).
- **Geometry / medium:** `--geo resources/geofiles/arca.geo` (ARCA, water) or
  `icecube.geo` (IceCube, ice); the medium is derived from the detector.
- **Propagator:** `--propagator PPC_CUDA` (GPU) or `PPC` (CPU, slow at PeV).
- `-n` events, `-s` seed, `--storage-prefix <dir>` output location.

## 3. Run it

**Single-PMT ν_τ in ARCA water** (legacy DOMs; isolates the water physics):

```bash
srun -p gpu_test --gpus=1 -c 4 --mem=8G -t 0:30:00 \
  python examples/run_prometheus_sim.py -n 10 -s 8300 \
  --final_1 TauMinus --final_2 Hadrons --emin 1e6 --emax 1e7 \
  --geo resources/geofiles/arca.geo --propagator PPC_CUDA \
  --ppc-exe  $PROM_ROOT/resources/PPC_executables/PPC_NEXTGEN_CUDA/ppc \
  --ppctables $PROM_ROOT/resources/PPC_tables/arca_water \
  --storage-prefix ./output/arca_water_singlepmt/
```

**Multi-PMT ν_τ in ARCA water** (2070-DOM × 31-PMT detector; per-PMT hits):

```bash
srun -p gpu_test --gpus=1 -c 4 --mem=16G -t 0:40:00 \
  python examples/run_prometheus_sim.py -n 25 -s 8500 \
  --final_1 TauMinus --final_2 Hadrons --emin 9.9e6 --emax 1.01e7 \
  --geo resources/geofiles/arca.geo --propagator PPC_CUDA \
  --multipmt --output-mode extended \
  --ppc-exe  $PROM_ROOT/resources/PPC_executables/PPC_NEXTGEN_CUDA/ppc \
  --ppctables $PROM_ROOT/resources/PPC_tables/arca_water \
  --storage-prefix ./output/arca_multipmt_tau/
```

For a clean **double-bang**, inject several events and pick the one with both
cascades contained (at 10 PeV the τ decay length is a few hundred metres, often
comparable to the array size). `examples/plot_doublebang.py` does this automatically.

## 4. How the τ decay is handled

The τ is propagated and decayed by **PROPOSAL** (the default `"new proposal"`
lepton propagator; decay is on by default via `config.…decay = True`):

1. LeptonInjector makes the CC vertex: `TauMinus` + `Hadrons`. The hadronic
   recoil is **cascade 1** (a point shower).
2. `prop.propagate(...)` transports the τ to its decay point, recording
   stochastic + continuous losses along the track (the faint connecting light).
3. `secondarys.decay_products()` become **child particles**; back in `ppc_sim`
   they are re-propagated. Neutrino daughters make no light (carry energy away);
   the visible daughters (e / hadrons / μ) deposit **cascade 2** at the decay
   point.

Net result = **hadronic cascade (vertex) + τ track + τ-decay cascade** = double-bang.
Decay channel and branching are sampled by PROPOSAL, so cascade-2 brightness varies
event to event (τ→μ dumps energy into a muon + ν's; τ→hadrons gives a bright bang).

## 5. Reading the output

Output: `<storage-prefix>/<seed>_photons.parquet`, with columns `mc_truth`
(always) and `photons` (per-hit arrays, only if hits were recorded).

```python
import glob, os, pandas as pd, numpy as np
df = pd.read_parquet(max(glob.glob("output/arca_multipmt_tau/*_photons.parquet"),
                         key=os.path.getmtime))   # newest by mtime
p = df["photons"].iloc[0]
```

- Minimal fields (always): `sensor_pos_{x,y,z}`, `string_id`, `sensor_id`, `t`, `id_idx`.
- `--output-mode extended` adds: **`pmt_id`**, `wavelength`, `photon_zenith/azimuth`,
  `om_zenith/azimuth`, `hit_x/hit_y/hit_z`.
- **`pmt_id` = PMT on the DOM (0–30)** — the real per-PMT index (extended only).
- ⚠️ **`id_idx` is NOT the PMT.** It is the producing final-state particle's
  `serialization_idx` (initial state = 0, final states = 1, 2, …) — only a few
  values per event. Use `pmt_id` for per-PMT work.
- `mc_truth` carries `initial_state_{energy,x,y,z,zenith,azimuth}` (the ν_τ vertex)
  and `final_state_*` arrays (used to locate the τ-decay cascade).

## 6. Gotchas

- **Pass `--ppc-exe` and `--ppctables` as ABSOLUTE paths.** Relative paths resolve
  against the package dir, PPC never runs, and (stderr suppressed) you just get
  "no photon hits" with no error.
- **`--emin` < `--emax`** strictly (see §2).
- **`--output-mode extended` under `PPC_CUDA`** requires the `construct_output`
  fix that reads the active propagator's sub-config (`.ppc_cuda`, not `.ppc`);
  without it the extended fields — including `pmt_id` — are silently dropped.
- After editing any repo `.py`, delete `__pycache__` or a run may execute stale
  bytecode.

## See also

- `examples/run_prometheus_sim.py` — the driver and its full flag set.
- `examples/plot_doublebang.py` — 3D double-bang + per-PMT DOM view (groups by `pmt_id`).
- `scripts/make_dx_dat.py`, `scripts/analyze_pmt_diag.py` — per-PMT diagnostics.
