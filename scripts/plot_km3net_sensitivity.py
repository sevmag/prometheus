#!/usr/bin/env python3
"""Plot the installed tabulated KM3NeT per-PMT angular sensitivity (what PPC
loads from km3net_as.dat) against the measured KM3NeT reference points, with the
old analytic curves for context. The installed line must coincide with the
measured points.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROM = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
AS_DAT = os.path.join(PROM, "resources/PPC_tables/arca_water/km3net_as.dat")
OUT = os.path.join(PROM, "output/light_source_geometry",
                   "km3net_pmt_sensitivity_vs_installed.png")

# Measured KM3NeT reference (cos_eta, f1), head-on = -1  [HANDOFF section 4]
REF = [
    (-1.00, 1.0000), (-0.95, 0.8301), (-0.90, 0.7357), (-0.85, 0.6619),
    (-0.80, 0.5998), (-0.75, 0.5410), (-0.70, 0.4874), (-0.65, 0.4387),
    (-0.60, 0.3947), (-0.55, 0.3544), (-0.50, 0.3190), (-0.45, 0.2777),
    (-0.40, 0.2445), (-0.35, 0.2101), (-0.30, 0.1818), (-0.25, 0.1535),
    (-0.20, 0.1276), (-0.15, 0.1025), (-0.10, 0.0788), (-0.05, 0.0586),
    (0.00, 0.0400), (0.05, 0.0233), (0.10, 0.0104), (0.15, 0.0039),
    (0.20, 0.0017), (0.25, 0.0000),
]


def analytic_f(x, beta):
    """Faithful reimplementation of PPC itype::f (Lambertian core + beta tail)."""
    FPI = np.pi

    def aS(v):
        al = np.arccos(np.clip(v, -1.0, 1.0))
        return al - np.sin(2 * al) / 2

    x = np.asarray(x, float)
    out = np.where(x > 0, x, 0.0)
    if beta < 1:
        y = np.sqrt(np.clip(1 - x * x, 0.0, None)) / beta
        m = y > 1
        yi = 1.0 / y[m]
        c = 1 - beta * beta
        out[m] += (aS(yi) / c - aS(yi * np.abs(x[m]) / np.sqrt(c)) * np.abs(x[m])) / FPI
    return out


def main():
    ce, f1 = np.loadtxt(AS_DAT, unpack=True)                 # installed table
    rc = np.array([p[0] for p in REF])
    rf = np.array([p[1] for p in REF])
    cosn = np.linspace(-1.0, 1.0, 400)
    old = analytic_f(-cosn, 0.49)                            # aligned f_ppc(-cos_eta,beta)
    fit = analytic_f(-cosn, 0.987)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    plt.figure(figsize=(7, 5))
    plt.plot(ce, f1, "-", lw=2, color="C0", label="installed km3net_as.dat (PPC)")
    plt.scatter(rc, rf, s=28, color="k", zorder=5, label="KM3NeT measured f1")
    plt.plot(cosn, old, "--", color="C3", label="old analytic beta=0.49")
    plt.plot(cosn, fit, ":", color="C2", label="analytic beta=0.987")
    plt.axvline(0.25, color="gray", ls=":", lw=0.8)
    plt.xlabel("cos eta   (photon dir . PMT axis; head-on = -1)")
    plt.ylabel("relative PMT sensitivity  f1")
    plt.title("ARCA multi-PMT angular sensitivity: installed vs measured")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT, dpi=120)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
