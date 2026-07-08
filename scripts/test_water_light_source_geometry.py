#!/usr/bin/env python3
"""ARCA-water isotropic-flasher geometry test.

Flashes a true-isotropic PPC light source (FWID=-1) from DOMs inside the ARCA
multi-PMT water array, takes the FIRST (direct) hit on each PMT, and histograms
the angle between each PMT's outward normal n and the direction from the PMT to
the source (S-P). Source-facing PMTs dominate first light, so the distribution
peaks toward 0 deg (cos -> +1), sharper for nearby OMs. Run on mimo in spack env
`prometheus`.
"""
import argparse
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

PROM = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
sys.path.insert(0, PROM)
TAB = os.path.join(PROM, "resources/PPC_tables/arca_water")
BIN_CPU = os.path.join(PROM, "resources/PPC_executables/PPC_NEXTGEN/ppc")
BIN_GPU = os.path.join(PROM, "resources/PPC_executables/PPC_NEXTGEN_CUDA/ppc")
OMR_ARCA = 0.2159  # ARCA multi-PMT OM radius [m] (matches build_arca_multipmt)

from prometheus.photon_propagation.utils.parse_ppc import parse_ppc  # noqa: E402


def build_detector():
    """Build the ARCA water multi-PMT Detector via the examples builder."""
    path = os.path.join(PROM, "examples/build_arca_multipmt.py")
    spec = importlib.util.spec_from_file_location("build_arca_multipmt", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_arca_multipmt_detector()


def pmt_dirs_of(detector):
    """Return the shared per-PMT (zenith_deg, azimuth_deg) list (index == pmt_id)."""
    return list(detector.modules[0].pmt_dirs)


def stage_tables(detector, tmpdir):
    """Stage nextgen tables into tmpdir (mirrors ppc_sim staging)."""
    shutil.copytree(TAB, tmpdir, dirs_exist_ok=True)
    detector.to_f2k(
        os.path.join(tmpdir, "geo-f2k"),
        serial_nos=[m.serial_no for m in detector.modules],
    )
    detector.to_om_conf(os.path.join(tmpdir, "om.conf"))
    detector.to_om_map(os.path.join(tmpdir, "om.map"))
    return tmpdir


def run_flasher(binary, tmpdir, str_id, dom_id, num, device=0):
    """Run the FWID=-1 isotropic flasher from DOM (str_id, dom_id).

    Returns (hits, source_pos_from_stderr_or_None, stderr_text).
    """
    out = os.path.join(tmpdir, f"hits_{str_id}_{dom_id}.txt")
    env = dict(os.environ, PPCTABLESDIR=tmpdir, NEXTGENDIR=tmpdir, FWID="-1")
    with open(out, "w") as fo:
        r = subprocess.run(
            [binary, str(str_id), str(dom_id), str(int(num)), str(device)],
            cwd=tmpdir, stdin=subprocess.DEVNULL, stdout=fo,
            stderr=subprocess.PIPE, env=env,
        )
    stderr = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        raise RuntimeError(f"PPC flasher failed rc={r.returncode}\n{stderr}")
    src = None
    for ln in stderr.splitlines():
        if "Flasher configured at" in ln:
            toks = ln.split("at", 1)[1].replace(",", " ").split()
            src = np.array([float(toks[0]), float(toks[1]), float(toks[2])])
    return parse_ppc(out), src, stderr


def pmt_normal(zen_deg, az_deg):
    """Outward PMT normal unit vector from (zenith_deg, azimuth_deg)."""
    th, ph = np.radians(zen_deg), np.radians(az_deg)
    return np.array([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])


def pick_sources(detector):
    """Pick 3 flashing DOMs inside the array: centroid-nearest, edge, near-top-interior."""
    keys = [m.key for m in detector.modules]
    pos = np.vstack([np.asarray(m.pos, float) for m in detector.modules])
    off = detector.offset
    center = keys[int(np.argmin(np.linalg.norm(pos - off, axis=1)))]
    edge = keys[int(np.argmax(np.linalg.norm(pos[:, :2] - off[:2], axis=1)))]
    zmax = pos[:, 2].max()
    interior = keys[int(np.argmin(
        np.linalg.norm(pos[:, :2] - off[:2], axis=1) + np.abs(pos[:, 2] - zmax)))]
    out = []
    for k in (center, edge, interior):
        if k not in out:
            out.append(k)
    return out


def _smoke():
    det = build_detector()
    assert len(det.modules) == 2070 and det.needs_nextgen()
    flash_key = pick_sources(det)[0]
    tmp = tempfile.mkdtemp(prefix="lsg_smoke_")
    try:
        stage_tables(det, tmp)
        hits, src, _ = run_flasher(BIN_CPU, tmp, flash_key[0], flash_key[1], 1_000_000)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    other = [(h.string_id, h.om_id) for h in hits if (h.string_id, h.om_id) != flash_key]
    upmt = {(h.string_id, h.om_id, h.pmt_id) for h in hits}
    assert hits and hits[0].pmt_id is not None, "no nextgen hits parsed"
    assert other, "no hits on DOMs other than the flashing one"
    print(f"SMOKE OK: {len(hits)} hits, {len(upmt)} unique PMTs, "
          f"flash_dom={flash_key}, source={src}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        _smoke()
