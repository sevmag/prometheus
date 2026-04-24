# Container Installation {#containers}

This page explains how to run **Prometheus** using container images.

Containers provide a **pre-configured environment** with all dependencies already installed.

---

## 🚀 First-Time Users (Recommended Path) {#first-time}

If you are new or unsure what to do:

1. Install Docker:
   👉 https://docs.docker.com/get-docker/

2. Run:

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

!!! tip "Quick start"
   This launches a ready-to-use Prometheus environment with no installation required.

---

## Docker vs Apptainer (Singularity) {#docker-vs-singularity}

### Docker (local machines)

* Best for **laptops and workstations**
* Easy to install and use

👉 Use Docker for local work

---

### Apptainer / Singularity (clusters)

* Designed for **HPC systems**
* Often pre-installed on clusters

👉 Use this on clusters or shared systems

---

## Available Images {#images}

| Tag           | Description       |
| ------------- | ----------------- |
| `:latest`     | CPU-only image    |
| `:latest-gpu` | GPU-enabled image |
| `:VERSION`    | Specific release  |

---

## Using Docker {#docker}

### Pull image

```bash
docker pull ghcr.io/harvard-neutrino/prometheus:latest
```

---

### Start shell

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

---

### Run example

```bash
docker run --rm -v "$PWD/output:/output" ghcr.io/harvard-neutrino/prometheus:latest python /opt/prometheus/examples/01_basic_water.py
```

!!! tip "Accessing output files"
   Use volume mounting (`-v "$PWD/output:/output"`) to access results on your local machine.

---

## GPU Support {#gpu}

!!! warning "GPU requirements"
   Requires the NVIDIA Container Toolkit:
   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

   ```bash
   docker run --rm -it --gpus all ghcr.io/harvard-neutrino/prometheus:latest-gpu
   ```

!!! tip "Troubleshooting GPU issues"
   If this fails, check your NVIDIA drivers and container toolkit installation.

---

## Using Apptainer / Singularity {#singularity}

### Load module

```bash
module load apptainer
```

---

### Pull container

```bash
singularity pull docker://ghcr.io/harvard-neutrino/prometheus:latest
```

---

### Run example

```bash
singularity exec prometheus_latest.sif python /opt/prometheus/examples/01_basic_water.py
```

---

## When Should I Use Containers? {#when}

Use containers if:

* You are on macOS or Windows
* Installation fails
* You are on a cluster
* You want reproducibility
