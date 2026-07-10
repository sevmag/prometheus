#!/usr/bin/env python3
"""Task 4 gate: verify the water PPC binary reproduces the measured optics CSVs.

Runs PPC_NEXTGEN with PPC_DUMP_OPTICS=1 on the arca_water tables, parses the
per-wavelength `OPTICS <lambda_nm> <L_sca[m]> <L_abs[m]> <n>` diagnostic, and
compares to KM3NeT_scattering.csv / KM3NeT_absorption.csv and the Mediterranean
refractive index. Prints "ALL OPTICS CHECKS PASS" on success.

Usage:  python3 validate_ppc_water_optics.py
"""
import os
import shutil
import subprocess
import tempfile

import numpy as np

PR = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
BIN = os.path.join(PR, "resources/PPC_executables/PPC_NEXTGEN/ppc")
TAB = os.path.join(PR, "resources/PPC_tables/arca_water")
A01, A2, A3, A4 = 1.32321, 16.2566, -4382.0, 1.1455e6           # Mediterranean n constants
TOL = 2.0                                                       # percent


def rd(p):
    xs, ys = [], []
    for ln in open(p):
        ln = ln.strip()
        if not ln or ln[0] == "#" or ln[0].isalpha():
            continue
        a, b = ln.split(",")
        xs.append(float(a))
        ys.append(float(b))
    o = np.argsort(xs)
    return np.array(xs)[o], np.array(ys)[o]


def main():
    sw, sl = rd(os.path.join(PR, "resources/KM3NeT_scattering.csv"))
    aw, al = rd(os.path.join(PR, "resources/KM3NeT_absorption.csv"))
    tmp = tempfile.mkdtemp(prefix="optval_")
    try:
        shutil.copytree(TAB, tmp, dirs_exist_ok=True)
        with open(os.path.join(tmp, "geo-f2k"), "w") as f:
            f.write("D1_1\t0x1\t0.0\t0.0\t-3200.0\t1\t1\n")
            f.write("D1_2\t0x2\t0.0\t0.0\t-3220.0\t1\t2\n")
        env = dict(os.environ, PPC_DUMP_OPTICS="1", PPCTABLESDIR=tmp)
        r = subprocess.run([BIN, "0"], cwd=tmp, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
        rows = sorted({(float(p[1]), float(p[2]), float(p[3]), float(p[4]))
                       for p in (ln.split() for ln in r.stderr.decode().splitlines())
                       if p and p[0] == "OPTICS"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not rows:
        print("FAIL: no OPTICS lines (is PPC_DUMP_OPTICS wired in?)")
        return 1
    ws = wa = 0.0
    nbad = 0
    n400 = None
    for w, ls, la, n in rows:
        if w < 305 or w > 715:
            continue
        cs = float(np.interp(w, sw, sl))
        ca = float(np.interp(w, aw, al))
        es = abs(ls - cs) / cs * 100
        ea = abs(la - ca) / ca * 100
        ws = max(ws, es)
        wa = max(wa, ea)
        nbad += (es > TOL or ea > TOL)
        if abs(w - 400) < 6:
            n400 = n
    nmed = A01 + (A2 + (A3 + A4 / 400.0) / 400.0) / 400.0
    print("worst sca err %.3f%%   worst abs err %.3f%%   rows>%.0f%%: %d" % (ws, wa, TOL, nbad))
    print("n(400): PPC=%.4f  Mediterranean=%.4f  (ice=1.319)" % (n400 if n400 else -1, nmed))
    ok = ws < TOL and wa < TOL and n400 is not None and abs(n400 - 1.354) < 0.01
    print("RESULT:", "ALL OPTICS CHECKS PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
