#!/usr/bin/env python3
"""Generic CLI Prometheus simulation driver (spack-env install).

Based on examples/02_basic_ice.py but fully CLI-configurable, for sbatch arrays.
Example:
  python examples/run_prometheus_sim.py -n 500 -s 1001 --final_1 TauMinus --emin 1e3 --emax 1e6
"""
import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Run a Prometheus simulation.")
    p.add_argument("-n", "--nevents", type=int, default=100)
    p.add_argument("-s", "--seed", type=int, default=1, help="run_number and RNG seed")
    p.add_argument("--emin", type=float, default=1e3)
    p.add_argument("--emax", type=float, default=1e4)
    p.add_argument("--final_1", default="MuMinus")
    p.add_argument("--final_2", default="Hadrons")
    p.add_argument("--geo", default="resources/geofiles/demo_ice.geo")
    p.add_argument("--storage-prefix", default="./output/")
    p.add_argument("--propagator", default="PPC", help="PPC (CPU) or PPC_CUDA (GPU)")
    p.add_argument("--ppc-exe", dest="ppc_exe", default=None,
                   help="override path to the ppc binary (else use the propagator's config default)")
    p.add_argument("--ppctables", dest="ppctables", default=None,
                   help="override path to the ppctables dir (else use the propagator's config default)")
    p.add_argument("--device", type=int, default=0,
                   help="ppc device index; the GPU id when --propagator PPC_CUDA")
    p.add_argument("--ranged", action="store_true", help="ranged injection (default: volume)")
    p.add_argument("--show-ppc-stderr", dest="show_ppc_stderr", action="store_true",
                   help="do not suppress PPC stderr (shows photons/hits per event; debugging)")
    p.add_argument("--multipmt", action="store_true",
                   help="build the multi-PMT ARCA detector (2070 DOMs x 31 PMT) instead of reading --geo")
    p.add_argument("--output-mode", dest="output_mode", default=None,
                   help="serializer output mode: minimal|standard|extended (extended adds pmt_id + hit positions)")
    return p.parse_args()


def main():
    a = parse_args()
    from prometheus import Prometheus, config
    try:
        import jax
        jax.config.update("jax_enable_x64", True)
        jax.config.update("jax_platform_name", "cpu")
    except Exception:
        pass

    config.run.run_number = a.seed
    config.run.random_state_seed = a.seed
    config.run.nevents = a.nevents
    config.run.storage_prefix = a.storage_prefix
    config.run.compact = True

    config.injection.name = "LeptonInjector"
    sim = config.injection.lepton_injector.simulation
    sim.is_ranged = a.ranged
    sim.final_state_1 = a.final_1
    sim.final_state_2 = a.final_2
    sim.minimal_energy = a.emin
    sim.maximal_energy = a.emax

    geo = Path(a.geo)
    if not geo.is_absolute() and not geo.exists():
        geo = Path(__file__).resolve().parent.parent / a.geo
    config.detector.geo_file = str(geo)

    config.photon_propagator.name = a.propagator
    # Select the matching sub-config: PPC -> .ppc (CPU), PPC_CUDA -> .ppc_cuda (GPU)
    pp_key = "ppc_cuda" if a.propagator.upper() == "PPC_CUDA" else "ppc"
    pp_sub = getattr(config.photon_propagator, pp_key)
    pp_sub.paths.force = True
    if a.ppc_exe:
        pp_sub.paths.ppc_exe = a.ppc_exe
    if a.ppctables:
        pp_sub.paths.ppctables = a.ppctables
    if a.show_ppc_stderr:
        pp_sub.simulation.supress_output = False
    pp_sub.simulation.device = a.device
    if a.output_mode:
        pp_sub.simulation.output_mode = a.output_mode

    if a.multipmt:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from build_arca_multipmt import build_arca_multipmt_detector
        Prometheus(detector=build_arca_multipmt_detector()).sim()
    else:
        Prometheus().sim()


if __name__ == "__main__":
    main()
