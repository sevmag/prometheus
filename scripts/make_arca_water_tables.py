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

PR = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
RES = os.path.join(PR, "resources")
OUT = os.path.join(RES, "PPC_tables", "arca_water")
UP = os.path.join(RES, "PPC_src", "ppc_upstream", "ice", "spice_ftp-v3m")
os.makedirs(OUT, exist_ok=True)


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
# icemodel.par: copy upstream (parses; values unused after patch)
shutil.copy(os.path.join(UP, "icemodel.par"), os.path.join(OUT, "icemodel.par"))
# 3) cfg.txt: 16 values -> HG, g=0.92, hole-ice/anisotropy/BFR OFF
with open(os.path.join(OUT, "cfg.txt"), "w") as f:
    f.write(
        "# arca water: over-R, eff, HG(0), g, [aniso], [holeice], [aniso2], "
        "[absaniso]  -- BFR omitted => OFF\n")
    for v in ["5", "1.0", "0", "0.92", "130.0", "0.0", "0.0", "0.0",
              "0.03", "100", "0.0", "0.92", "0.0", "0.0", "0.0", "0.0"]:
        f.write(v + "\n")
# 4) wv.dat: Cherenkov(1/lambda^2) x high-QE, CDF over 301..719 nm
qw, qq = rd(os.path.join(RES, "KM3NeT_QE_jpp_highQE.csv"))
grid = np.arange(300.0, 720.0 + 1e-6, 10.0)
qe = np.clip(np.interp(grid, qw, qq), 1e-9, None)
dens = (1.0 / grid**2) * (qe / 100.0)         # Cherenkov(1/lambda^2) x QE density
cdf = np.concatenate([[0.0], np.cumsum((dens[1:] + dens[:-1]) / 2 * np.diff(grid))])
cdf /= cdf[-1]
g2 = [grid[0]]
c2 = [0.0]                                    # keep only strictly-increasing CDF (drop QE~0 tail)
for i in range(1, len(grid)):
    if cdf[i] > c2[-1] + 1e-6:
        g2.append(grid[i])
        c2.append(cdf[i])
c2[-1] = 1.0                                  # force exact 1 at last kept point
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
        f.write(f"{i} {r*math.cos(th):.6f} {r*math.sin(th):.6f} {z:.6f}\n")
# 6) om.wv_1.0: wavelength_nm  eff_area_cm2 (QE/100 * photocathode area)
AREA = 45.0
with open(os.path.join(OUT, "om.wv_1.0"), "w") as f:
    for w, q in zip(qw, qq):
        f.write(f"{w:.1f} {(q/100.0)*AREA:.6f}\n")
# 7) eff-f2k, rnd.txt, as.dat from upstream (parse-compatible)
for fn in ("eff-f2k", "rnd.txt", "as.dat"):
    shutil.copy(os.path.join(UP, fn), os.path.join(OUT, fn))
print("wrote", OUT)
print("files:", sorted(os.listdir(OUT)))
