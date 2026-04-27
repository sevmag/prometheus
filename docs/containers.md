# Container Installation

This page explains how to run Prometheus using container images. Containers provide a pre-configured environment with all dependencies already installed.

## First-Time Users

If you are new or unsure what to do:

1. Install Docker from the [Docker website](https://docs.docker.com/get-docker/).

2. Run:

```sh
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

!!! tip
    This launches a ready-to-use Prometheus environment with no installation required.

## Docker vs Apptainer (Singularity)

### Docker (local machines)

- Best for laptops and workstations
- Easy to install and use

### Apptainer / Singularity (clusters)

- Designed for HPC systems
- Often pre-installed on clusters

## Available Images

| Tag           | Description       |
| ------------- | ----------------- |
| `:latest`     | CPU-only image    |
| `:latest-gpu` | GPU-enabled image |
| `:VERSION`    | Specific release  |

## Using Docker

### Pull image

```sh
docker pull ghcr.io/harvard-neutrino/prometheus:latest
```

### Start shell

```sh
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

### Run example

```sh
docker run --rm -v "$PWD/output:/output" ghcr.io/harvard-neutrino/prometheus:latest python /opt/prometheus/examples/01_basic_water.py
```

!!! tip
    Use volume mounting (`-v "$PWD/output:/output"`) to access results on your local machine.

## GPU Support

!!! warning
    Requires the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```sh
docker run --rm -it --gpus all ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

!!! tip
    If this fails, check your NVIDIA drivers and container toolkit installation.

## Using Apptainer / Singularity

### Load module

```sh
module load apptainer
```

### Pull container

```sh
singularity pull docker://ghcr.io/harvard-neutrino/prometheus:latest
```

### Run example

```sh
singularity exec prometheus_latest.sif python /opt/prometheus/examples/01_basic_water.py
```

## When Should I Use Containers?

Use containers if:

- You are on macOS or Windows
- The source installation fails
- You are on a cluster
- You want a reproducible environment
