#!/usr/bin/env python3
"""Generate resources/PPC_tables/arca_water for the nextgen+water PPC binary.
Optics come from the measured CSVs (patch reads sca_len/abs_len); ice-model
files are placeholders in the UPSTREAM format (patch overrides sca/abs).
Depth grid spans ARCA (DOMs map to depth = -z = 2888..3500 m). cfg: HG, g=0.92,
anisotropy/hole-ice/BFR OFF."""

import math
import os
import shutil

import numpy as np

PR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(PR, "resources")
OUT = os.path.join(RES, "PPC_tables", "arca_water")
# icemodel.par, rnd.txt and as.dat are verbatim copies of icecube/ppc's
# ice/spice_ftp-v3m. PPC_UPSTREAM_ICE may point at that directory in an
# icecube/ppc checkout to refresh them; unset, the copies shipped in OUT are kept.
UP = os.environ.get("PPC_UPSTREAM_ICE")
os.makedirs(OUT, exist_ok=True)


def upstream_copy(fn):
    dst = os.path.join(OUT, fn)
    if UP:
        shutil.copy(os.path.join(UP, fn), dst)
    elif not os.path.exists(dst):
        raise SystemExit(
            f"{fn} is missing from {OUT} and PPC_UPSTREAM_ICE is not set; "
            "point it at ice/spice_ftp-v3m in an icecube/ppc checkout"
        )


def rd(p):
    xs = []
    ys = []
    for ln in open(p):
        ln = ln.strip()
        if not ln or ln[0] == "#" or ln[0].isalpha():
            continue
        a, b = ln.split(",")
        xs.append(float(a))
        ys.append(float(b))
    o = np.argsort(xs)
    return np.array(xs)[o], np.array(ys)[o]


# 1) optics tables: wavelength_nm  length_m (ascending) -- read by the patch
sw, sl = rd(os.path.join(RES, "KM3NeT_scattering.csv"))
aw, al = rd(os.path.join(RES, "KM3NeT_absorption.csv"))
with open(os.path.join(OUT, "sca_len.dat"), "w") as f:
    for w, L in zip(sw, sl):
        f.write(f"{w:.4f} {L:.6f}\n")
with open(os.path.join(OUT, "abs_len.dat"), "w") as f:
    for w, L in zip(aw, al):
        f.write(f"{w:.4f} {L:.6f}\n")
# 2) icemodel.dat: wide UNIFORM placeholder grid (depth be ba td), covers ARCA depths
with open(os.path.join(OUT, "icemodel.dat"), "w") as f:
    for d in range(500, 4001, 100):
        f.write(f"{d}.0 0.02 0.01 0.0\n")
# icemodel.par: upstream verbatim (parses; values unused after patch)
upstream_copy("icemodel.par")
# 3) cfg.txt: 16 values -> HG, g=0.92, hole-ice/anisotropy/BFR OFF
with open(os.path.join(OUT, "cfg.txt"), "w") as f:
    f.write(
        "# arca water: over-R, eff, HG(0), g, [aniso], [holeice], [aniso2], "
        "[absaniso]  -- BFR omitted => OFF\n"
    )
    for v in [
        "5",
        "1.0",
        "0",
        "0.92",
        "130.0",
        "0.0",
        "0.0",
        "0.0",
        "0.03",
        "100",
        "0.0",
        "0.92",
        "0.0",
        "0.0",
        "0.0",
        "0.0",
    ]:
        f.write(v + "\n")
    f.write(
        "# seawater density [g/cm^3], water mode only "
        "(read as v[16] when sca_len/abs_len present)\n"
    )
    f.write("1.04\n")
# 4) wv.dat: Cherenkov(1/lambda^2) x high-QE, CDF over 301..719 nm
qw, qq = rd(os.path.join(RES, "KM3NeT_QE_jpp_highQE.csv"))
grid = np.arange(300.0, 720.0 + 1e-6, 10.0)
qe = np.clip(np.interp(grid, qw, qq), 1e-9, None)
dens = (1.0 / grid**2) * (qe / 100.0)  # Cherenkov(1/lambda^2) x QE density
cdf = np.concatenate([[0.0], np.cumsum((dens[1:] + dens[:-1]) / 2 * np.diff(grid))])
cdf /= cdf[-1]
g2 = [grid[0]]
c2 = [0.0]  # keep only strictly-increasing CDF (drop QE~0 tail)
for i in range(1, len(grid)):
    if cdf[i] > c2[-1] + 1e-6:
        g2.append(grid[i])
        c2.append(cdf[i])
c2[-1] = 1.0  # force exact 1 at last kept point
with open(os.path.join(OUT, "wv.dat"), "w") as f:
    for c, wl in zip(c2, g2):
        f.write(f"{c:.8f} {wl:.0f}.\n")
# 5) om.dirs: 1000 uniform sphere directions (idx x y z)
with open(os.path.join(OUT, "om.dirs"), "w") as f:
    n = 1000
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0, 1 - z * z))
        th = ga * i
        f.write(f"{i} {r * math.cos(th):.6f} {r * math.sin(th):.6f} {z:.6f}\n")
# 6) om.wv_1.0: wavelength_nm  eff_area_cm2 (QE/100 * photocathode area)
# Jpp JPhysics/KM3NeT.hh getPhotocathodeArea(): the collection area per PMT
# that the collaboration's own simulation pairs with exactly this QE table and
# angular-acceptance curve (normalized to 1 head-on, collection efficiency
# folded into QE). Larger than the bare 3" photocathode (~45 cm^2) because it
# includes the reflector-ring gain.
AREA = 70.768818
with open(os.path.join(OUT, "om.wv_1.0"), "w") as f:
    for w, q in zip(qw, qq):
        f.write(f"{w:.1f} {(q / 100.0) * AREA:.6f}\n")
# 7) rnd.txt, as.dat from upstream (parse-compatible).
# No eff-f2k: the upstream one is IceCube's DeepCore high-QE list (strings
# 36-86), whose keys collide with ARCA string numbering and route those DOMs
# to a nonexistent om.wv_1.1 table, silently dropping all their hits. With no
# eff-f2k every DOM gets rde=1, wavelength-type 0, which is what ARCA needs.
for fn in ("rnd.txt", "as.dat"):
    upstream_copy(fn)
print("wrote", OUT)
print("files:", sorted(os.listdir(OUT)))
