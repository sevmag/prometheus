# Container Installation {#containers}

This page explains how to run **Prometheus** using container images.

Containers provide a **pre-configured environment** with all dependencies already installed. This avoids common issues with compiling physics software.

---

## 🚀 First-Time Users (Recommended Path) {#first-time}

If you are new to Prometheus or unsure which setup to use:

1. Install Docker:
   👉 https://docs.docker.com/get-docker/

2. Run this command:

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

That’s it — you are now inside an environment where Prometheus is ready to use.

!!! tip
This is the fastest and most reliable way to get started, especially on macOS or Windows.

---

## Docker vs Apptainer (Singularity) {#docker-vs-singularity}

### Docker (recommended for local use)

* Best for **laptops and workstations**
* Easy to install and use
* Ideal for development and testing

👉 Use Docker if you are working on your **own machine**

---

### Apptainer / Singularity (recommended for clusters)

* Designed for **HPC environments**
* Often pre-installed on university clusters
* Does not require administrator privileges

👉 Use Apptainer/Singularity if you are working on a **cluster**

---

## Available Images {#images}

Prometheus images are hosted on GitHub Container Registry:

| Tag            | Description          |
| -------------- | -------------------- |
| `:latest`      | CPU-only image       |
| `:latest-gpu`  | GPU-enabled image    |
| `:VERSION`     | Specific release     |
| `:VERSION-gpu` | Specific GPU release |

---

## Using Docker {#docker}

### 1. Pull the Image

```bash
docker pull ghcr.io/harvard-neutrino/prometheus:latest
```

---

### 2. Start an Interactive Shell

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

---

### 3. Run an Example

```bash
docker run --rm -v "$PWD/output:/output" \
    ghcr.io/harvard-neutrino/prometheus:latest \
    python /opt/prometheus/examples/01_basic_water.py
```

!!! note
The `-v "$PWD/output:/output"` option makes results available on your host machine.

---

## GPU Support {#gpu}

!!! warning
Requires the
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

```bash
docker run --rm -it --gpus all \
    ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

---

## Using Apptainer / Singularity {#singularity}

### 1. Load Apptainer

```bash
module load apptainer
```

---

### 2. Pull the Container

```bash
singularity pull docker://ghcr.io/harvard-neutrino/prometheus:latest
```

---

### 3. Run an Example

```bash
singularity exec prometheus_latest.sif \
    python /opt/prometheus/examples/01_basic_water.py
```

---

## When Should I Use Containers? {#when}

Use containers if:

* You are on **macOS or Windows**
* Installation fails on your system
* You are working on a **cluster**
* You want a **reproducible environment**
