# Docker containers for Prometheus

Two images are available on the [GitHub Container Registry (GHCR)](https://ghcr.io/harvard-neutrino/prometheus):

| Tag pattern | Contents |
|---|---|
| `ghcr.io/harvard-neutrino/prometheus:VERSION` | CPU-only build |
| `ghcr.io/harvard-neutrino/prometheus:VERSION-gpu` | CUDA GPU build |
| `ghcr.io/harvard-neutrino/prometheus:latest` | Latest CPU release |
| `ghcr.io/harvard-neutrino/prometheus:latest-gpu` | Latest GPU release |

---

## Pulling the image

```bash
# CPU image
docker pull ghcr.io/harvard-neutrino/prometheus:latest

# GPU image
docker pull ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

---

## Running

### CPU (interactive shell)

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

### CPU (run a script)

```bash
docker run --rm \
    -v "$PWD/output:/output" \
    ghcr.io/harvard-neutrino/prometheus:latest \
    python /opt/prometheus/examples/01_basic_water.py
```

### GPU (requires NVIDIA Container Toolkit on host)

```bash
# First install the toolkit if needed:
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

docker run --rm -it --gpus all ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

---

## Converting to a Singularity/Apptainer image

GHCR images are publicly readable without a login, so conversion is a single command:

```bash
singularity pull docker://ghcr.io/harvard-neutrino/prometheus:latest
# Creates: prometheus_latest.sif
```

Run on an HPC cluster:

```bash
singularity exec prometheus_latest.sif python /opt/prometheus/examples/01_basic_water.py
```

GPU job on a SLURM cluster:

```bash
singularity exec --nv \
    docker://ghcr.io/harvard-neutrino/prometheus:latest-gpu \
    python my_job.py
```

---

## Building locally

The build context is the repository root. Build both images from there:

```bash
# CPU image
docker build -f container/Dockerfile -t prometheus:cpu .

# GPU image (default SM arch 89 = Ada Lovelace / RTX 40xx)
docker build -f container/Dockerfile.gpu -t prometheus:gpu .

# GPU image for A100 (SM 80) or H100 (SM 90)
docker build -f container/Dockerfile.gpu --build-arg SM_ARCH=80 -t prometheus:gpu-sm80 .
```

### SM architecture reference

| `SM_ARCH` | Architecture | Example GPUs |
|---|---|---|
| `75` | Turing | RTX 20xx, T4 |
| `80` | Ampere | A100, RTX 30xx |
| `86` | Ampere | RTX 30xx (consumer) |
| `89` | Ada Lovelace (default) | RTX 40xx, L40S |
| `90` | Hopper | H100 |

---

## Testing locally before pushing

Use `scripts/docker_test.sh` to build and validate an image offline:

```bash
# Build + smoke tests + fast unit tests (CPU, ~5 min)
bash scripts/docker_test.sh

# Same for GPU image
bash scripts/docker_test.sh --gpu

# Include the 100-event physics regression test (~8 min extra)
bash scripts/docker_test.sh --e2e

# Test a pre-built image without rebuilding
bash scripts/docker_test.sh --no-build --tag prometheus:cpu
```

---

## Publishing a new release

Images are built and pushed to GHCR via GitHub Actions under **Actions → Publish Docker images** (manual dispatch only).

Inputs:

| Field | Description |
|---|---|
| `version` | Tag name, e.g. `v2.0` |
| `variant` | `cpu`, `gpu`, or `both` |
| `sm_arch` | CUDA SM arch for the GPU build (default `89`) |

This produces:
- `ghcr.io/harvard-neutrino/prometheus:v2.0` (CPU)
- `ghcr.io/harvard-neutrino/prometheus:latest` (CPU latest)
- `ghcr.io/harvard-neutrino/prometheus:v2.0-gpu` (GPU)
- `ghcr.io/harvard-neutrino/prometheus:latest-gpu` (GPU latest)
