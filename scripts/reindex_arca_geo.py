#!/usr/bin/env python3
"""One-shot migration: re-index ARCA geo IDs from 0-based to 1-based.

Adds 1 to the string (column 4) and OM (column 5) of every module line in a
Prometheus geofile, so ARCA matches PPC/IceCube/KM3NeT 1-based conventions and
PPC's reserved str==0 flasher encoding no longer collides with a real string.
Idempotent: refuses to run if the geo is already 1-based (min string id != 0).
Positions (x/y/z) are left byte-identical.
"""
import argparse
import os
import sys

PROM = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
DEFAULT_GEO = os.path.join(PROM, "resources/geofiles/arca.geo")


def reindex(path):
    with open(path) as f:
        lines = f.readlines()
    try:
        start = lines.index("### Modules ###\n") + 1
    except ValueError:
        sys.exit(f"no '### Modules ###' header in {path}")

    rows, strs, oms = [], [], []
    for i in range(start, len(lines)):
        c = lines[i].rstrip("\n").split("\t")
        if len(c) < 5:
            continue
        rows.append(i)
        strs.append(int(c[3]))
        oms.append(int(c[4]))
    if not rows:
        sys.exit(f"no module rows after header in {path}")
    if min(strs) != 0 or min(oms) != 0:
        sys.exit(f"refusing: geo not 0-based (min string={min(strs)}, min om={min(oms)}); "
                 "already migrated?")

    for i in rows:
        c = lines[i].rstrip("\n").split("\t")
        c[3] = str(int(c[3]) + 1)
        c[4] = str(int(c[4]) + 1)
        lines[i] = "\t".join(c) + "\n"

    with open(path, "w") as f:
        f.writelines(lines)

    print(f"reindexed {len(rows)} modules in {path}: "
          f"strings {min(strs)}..{max(strs)} -> {min(strs)+1}..{max(strs)+1}, "
          f"oms {min(oms)}..{max(oms)} -> {min(oms)+1}..{max(oms)+1}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default=DEFAULT_GEO)
    reindex(ap.parse_args().geo)
