#!/usr/bin/env python3
"""Generate a dx.dat (per-DOM cable azimuth) for the ARCA multi-PMT detector.

dx.dat feeds PPC's getPMT() per-DOM cable azimuth ``ph`` (ini.cxx:955). Format is
one whitespace-separated line per DOM::

    string  om  cable_azimuth_deg  r

The 4th column ``r`` is read but *ignored* by this PPC build (only the azimuth is
stored); it must still be present so the ``>>`` extraction succeeds. A negative
azimuth means "unset" (PPC wraps it by +360).

Modes -- the 3-way experiment for the per-PMT assignment bug
(HANDOFF_multipmt_pmt_assignment_bug.md):

  none     remove the target dx.dat  -> baseline: getPMT ph=-1, rotation skipped.
  uniform  same azimuth (default 0) for every DOM -> ph constant; with cable=0 in
           om.conf this is an IDENTITY rotation (predicted no-op vs `none`).
  random   independent U(0,360) per DOM -> the only mode that injects genuine
           per-DOM azimuthal diversity.

Write to the ppctables dir the propagator copies from (default
resources/PPC_tables/arca_water/dx.dat); ppc_photon_propagator.py stages dx.dat
into the PPC tmpdir when present. Keys are read from the same geofile as
build_arca_multipmt, so they match the om.map/geo-f2k DOM identities PPC uses.

Examples::

    python scripts/make_dx_dat.py --mode none
    python scripts/make_dx_dat.py --mode uniform --value 0
    python scripts/make_dx_dat.py --mode random --seed 0
"""
import argparse
import os
import random

PR = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
GEO_DEFAULT = os.path.join(PR, "resources", "geofiles", "arca.geo")
OUT_DEFAULT = os.path.join(PR, "resources", "PPC_tables", "arca_water", "dx.dat")


def load_dom_keys(geo):
    """Return the ordered list of ``(string, om)`` DOM keys from a geofile.

    Mirrors ``build_arca_multipmt.build_arca_multipmt_detector`` (same
    ``### Modules ###`` marker, tab split, ``len(c) >= 5`` guard) so the dx.dat
    keys match the DOM identities PPC looks up.
    """
    lines = open(geo).readlines()
    start = lines.index("### Modules ###\n") + 1
    keys = []
    for ln in lines[start:]:
        c = ln.strip("\n").split("\t")
        if len(c) < 5:
            continue
        keys.append((int(c[3]), int(c[4])))
    return keys


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--mode", choices=["none", "uniform", "random"], required=True)
    ap.add_argument(
        "--value", type=float, default=0.0,
        help="cable azimuth [deg] for --mode uniform (default 0)",
    )
    ap.add_argument(
        "--seed", type=int, default=0, help="RNG seed for --mode random (default 0)"
    )
    ap.add_argument(
        "--radius", type=float, default=0.2159,
        help="4th-column r [m]; read but ignored by PPC (default 0.2159)",
    )
    ap.add_argument("--geo", default=GEO_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    if args.mode == "none":
        if os.path.exists(args.out):
            os.remove(args.out)
            print(f"removed {args.out} (baseline: no dx.dat staged)")
        else:
            print(f"no dx.dat at {args.out}; baseline already in place")
        return

    keys = load_dom_keys(args.geo)
    rng = random.Random(args.seed)
    with open(args.out, "w") as f:
        for s, om in keys:
            azi = args.value if args.mode == "uniform" else rng.uniform(0.0, 360.0)
            f.write(f"{s}\t{om}\t{azi:.4f}\t{args.radius:.4f}\n")

    detail = (
        f"value={args.value}" if args.mode == "uniform" else f"seed={args.seed}"
    )
    print(f"wrote {args.out}: {len(keys)} DOMs, mode={args.mode} {detail}")


if __name__ == "__main__":
    main()
