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


def first_hit_per_pmt(hits):
    """Keep the earliest-time Hit for each (string, om, pmt) key."""
    first = {}
    for h in hits:
        key = (h.string_id, h.om_id, h.pmt_id)
        if key not in first or h.time < first[key].time:
            first[key] = h
    return first


def analyze(detector, pmt_dirs, hits, source_pos, flash_key=None):
    """Per hit PMT (first hit): angle between normal n and (source - PMT_center).

    Returns array cols [string, om, pmt, theta_deg, cos, dist_m].
    """
    posmap = {m.key: np.asarray(m.pos, float) for m in detector.modules}
    normals = [pmt_normal(z, a) for (z, a) in pmt_dirs]
    rows = []
    for (s, o, p), h in first_hit_per_pmt(hits).items():
        if (s, o) not in posmap or (s, o) == flash_key:
            continue
        D = posmap[(s, o)]
        n = normals[p]
        P = D + OMR_ARCA * n
        v = source_pos - P
        cos = float(np.dot(n, v) / (np.linalg.norm(n) * np.linalg.norm(v)))
        cos = max(-1.0, min(1.0, cos))
        rows.append((s, o, p, np.degrees(np.arccos(cos)), cos,
                     float(np.linalg.norm(source_pos - D))))
    return np.array(rows, dtype=float) if rows else np.empty((0, 6))


def plot_source(data, source_key, source_pos, outdir, near_m=75.0):
    """Write theta/cos histograms (near vs far) and return a metrics dict."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(outdir, exist_ok=True)
    theta, cos, dist = data[:, 3], data[:, 4], data[:, 5]
    near = dist < near_m
    far = ~near
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, arr, xlabel, bins, rng, mark in [
        (axes[0], theta, "angle(n, S-P) [deg]", 36, (0, 180), 0),
        (axes[1], cos, "cos(angle)  (face-on -> +1)", 40, (-1, 1), 1),
    ]:
        if near.sum():
            ax.hist(arr[near], bins=bins, range=rng, histtype="step",
                    density=True, label=f"near (<{near_m:.0f} m) N={int(near.sum())}")
        if far.sum():
            ax.hist(arr[far], bins=bins, range=rng, histtype="step",
                    density=True, label=f"far N={int(far.sum())}")
        ax.axvline(mark, color="k", ls=":")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("pdf")
        ax.legend()
    fig.suptitle(f"ARCA water isotropic flasher | source DOM {source_key} "
                 f"@ {np.round(source_pos, 1)}")
    fig.tight_layout()
    png = os.path.join(outdir, f"light_source_geom_{source_key[0]}_{source_key[1]}.png")
    fig.savefig(png, dpi=120)
    plt.close(fig)
    return png, {
        "source_key": [int(source_key[0]), int(source_key[1])],
        "source_pos": [float(x) for x in source_pos],
        "n_pmt_hits": int(len(data)),
        "mean_cos_all": float(np.mean(cos)) if len(cos) else None,
        "mean_cos_near": float(np.mean(cos[near])) if near.sum() else None,
        "mean_cos_far": float(np.mean(cos[far])) if far.sum() else None,
        "median_theta_near": float(np.median(theta[near])) if near.sum() else None,
    }


def _analyze_smoke():
    det = build_detector()
    dirs = pmt_dirs_of(det)
    flash_key = pick_sources(det)[0]
    outdir = os.path.join(PROM, "output/light_source_geometry")
    tmp = tempfile.mkdtemp(prefix="lsg_an_")
    try:
        stage_tables(det, tmp)
        hits, src, _ = run_flasher(BIN_CPU, tmp, flash_key[0], flash_key[1], 10_000_000)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    source_pos = np.asarray(det[flash_key].pos, float)  # geo frame, same as PMT centers
    data = analyze(det, dirs, hits, source_pos, flash_key=flash_key)
    assert len(data) > 0, "no PMT rows to analyze"
    assert np.all((data[:, 3] >= 0) & (data[:, 3] <= 180))
    assert np.all((data[:, 4] >= -1) & (data[:, 4] <= 1))
    png, metrics = plot_source(data, flash_key, source_pos, outdir)
    print("ANALYZE_SMOKE " + json.dumps(metrics))
    print("PNG " + png)


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
    ap.add_argument("--analyze-smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        _smoke()
    elif args.analyze_smoke:
        _analyze_smoke()
