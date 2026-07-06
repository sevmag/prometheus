#!/usr/bin/env python3
"""Compare PROM_PMT_DIAG dumps across the 3-way dx.dat experiment.

Ingests one or more diagnostic files written by ``_dump_pmt_diag`` in
``ppc_photon_propagator.py`` (enable with ``PROM_PMT_DIAG=<file>``) and prints a
side-by-side table plus a heuristic verdict for the per-PMT assignment bug
(HANDOFF_multipmt_pmt_assignment_bug.md).

Each diag file contains, across one or more ``# ppc_sim`` blocks:
    # type <t>: npmt=<k> ndistinct=<d> zen[min,max]=[..,..]
    # hits: string om pmt_id pth pph dth dph
    <string> <om> <pmt_id> <pth> <pph> <dth> <dph>
where ``pth`` is the PHOTON-direction zenith that drives getPMT selection.

Usage::

    python scripts/analyze_pmt_diag.py                       # globs output/pmt_diag_*.txt
    python scripts/analyze_pmt_diag.py a.txt b.txt c.txt     # explicit files
"""
import glob
import math
import os
import sys
from array import array
from collections import Counter

N_PMT = 31
# Preferred display order for the standard experiment arms.
ARM_ORDER = {"none": 0, "uniform": 1, "random": 2}


def arm_label(path):
    """Turn output/pmt_diag_random.txt -> 'random' (else the bare basename)."""
    base = os.path.basename(path)
    for pre in ("pmt_diag_", "pmt_diag"):
        if base.startswith(pre):
            base = base[len(pre):]
            break
    return base[:-4] if base.endswith(".txt") else base or os.path.basename(path)


def analyze(path):
    """Single streaming pass over a diag file -> metrics dict."""
    total = 0
    pmt_counts = Counter()
    dom_pmts = {}            # (string, om) -> set of pmt_id
    pth = array("f")         # compact store of photon-direction zenith
    type_headers = set()     # dedup identical per-block type lines

    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                if line.startswith("# type"):
                    type_headers.add(line.strip())
                continue
            t = line.split()
            if len(t) < 7:
                continue
            try:
                s, om, pmt, p = int(t[0]), int(t[1]), int(t[2]), float(t[3])
            except ValueError:
                continue
            total += 1
            pmt_counts[pmt] += 1
            dom_pmts.setdefault((s, om), set()).add(pmt)
            pth.append(p)

    m = {
        "path": path,
        "hits": total,
        "doms": len(dom_pmts),
        "pmt_counts": pmt_counts,
        "n_pmt_used": len(pmt_counts),
        "type_headers": sorted(type_headers),
    }
    if total:
        top_pmt, top_n = pmt_counts.most_common(1)[0]
        m["top_pmt"] = top_pmt
        m["top_frac"] = top_n / total
        per_dom = [len(v) for v in dom_pmts.values()]
        m["pmts_per_dom_mean"] = sum(per_dom) / len(per_dom)
        m["pmts_per_dom_max"] = max(per_dom)
        # Photon-direction spread. Raw PPC angle units are unverified: if any
        # |pth| exceeds ~pi it must be degrees, so convert before cos().
        mx = max((abs(x) for x in pth), default=0.0)
        deg = mx > math.pi + 1e-3
        fac = math.pi / 180.0 if deg else 1.0
        m["pth_units"] = "deg" if deg else "rad"
        n = len(pth)
        s1 = s2 = 0.0
        dmin, dmax = math.inf, -math.inf
        for x in pth:
            z = math.cos(x * fac)
            s1 += z
            s2 += z * z
            dmin = z if z < dmin else dmin
            dmax = z if z > dmax else dmax
        mean = s1 / n
        m["dirz_min"], m["dirz_max"] = dmin, dmax
        m["dirz_std"] = math.sqrt(max(0.0, s2 / n - mean * mean))
    return m


def _fmt(m, key, spec="{}"):
    return spec.format(m[key]) if key in m else "-"


def print_table(metrics):
    labels = [arm_label(m["path"]) for m in metrics]
    rows = [
        ("hits", lambda m: _fmt(m, "hits", "{:,}")),
        ("DOMs lit", lambda m: _fmt(m, "doms", "{:,}")),
        (f"PMTs used /{N_PMT}", lambda m: _fmt(m, "n_pmt_used")),
        ("top PMT (id: %)",
         lambda m: f"{m['top_pmt']}: {100 * m['top_frac']:.1f}%" if "top_pmt" in m else "-"),
        ("PMTs/DOM mean", lambda m: _fmt(m, "pmts_per_dom_mean", "{:.2f}")),
        ("PMTs/DOM max", lambda m: _fmt(m, "pmts_per_dom_max")),
        ("dir_z min", lambda m: _fmt(m, "dirz_min", "{:+.3f}")),
        ("dir_z max", lambda m: _fmt(m, "dirz_max", "{:+.3f}")),
        ("dir_z std", lambda m: _fmt(m, "dirz_std", "{:.3f}")),
        ("pth units", lambda m: _fmt(m, "pth_units")),
    ]
    w0 = max(len(r[0]) for r in rows)
    cols = [max(len(lbl), 10) for lbl in labels]
    header = " " * w0 + "  " + "  ".join(lbl.rjust(c) for lbl, c in zip(labels, cols))
    print(header)
    print("-" * len(header))
    for name, fn in rows:
        cells = [fn(m).rjust(c) for m, c in zip(metrics, cols)]
        print(name.ljust(w0) + "  " + "  ".join(cells))

    # PMT geometry sanity (should be identical across arms).
    print("\nPMT dirs (from om.conf, should be non-degenerate & identical across arms):")
    for lbl, m in zip(labels, metrics):
        th = m["type_headers"]
        print(f"  {lbl}: " + ("; ".join(h[2:] for h in th) if th else "<none parsed>"))


def verdict(metrics):
    by = {arm_label(m["path"]): m for m in metrics}
    print("\nVerdict (heuristic):")
    none, uni, rnd = by.get("none"), by.get("uniform"), by.get("random")

    def dominates(m):
        return m and m.get("top_frac", 0) > 0.5 and m.get("n_pmt_used", 99) <= 5

    if none and uni and none.get("hits") and uni.get("hits"):
        same = (none["n_pmt_used"] == uni["n_pmt_used"]
                and none.get("top_pmt") == uni.get("top_pmt")
                and abs(none["top_frac"] - uni["top_frac"]) < 0.01)
        print("  - uniform " + ("==" if same else "!=") + " none  ->  "
              + ("dx.dat=0 is a NO-OP, as predicted (identity rotation)."
                 if same else "uniform differs from none (unexpected; check cable/om.conf)."))
    if rnd and rnd.get("hits"):
        if dominates(rnd):
            print("  - random STILL collapses -> cable clocking is not the cause; "
                  "the zenith-ring selection / frame is (getPMT ignores tilt).")
        else:
            print("  - random spreads the hits -> per-DOM cable azimuth matters; "
                  "a real dx.dat (not uniform 0) is needed.")
    for lbl in ("none", "uniform", "random"):
        m = by.get(lbl)
        if m and m.get("hits") and m.get("dirz_std", 0) > 0.2 and dominates(m):
            print(f"  - {lbl}: photon dir_z varies (std={m['dirz_std']:.2f}) but PMTs "
                  f"collapse -> bug is downstream of photon transport, in assignment.")
            break


def main():
    paths = sys.argv[1:]
    if not paths:
        paths = sorted(glob.glob("output/pmt_diag_*.txt"))
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        sys.exit("no diag files given and none matched output/pmt_diag_*.txt")
    paths.sort(key=lambda p: ARM_ORDER.get(arm_label(p), 99))
    metrics = [analyze(p) for p in paths]
    print(f"Analyzed {len(metrics)} file(s): " + ", ".join(p for p in paths) + "\n")
    print_table(metrics)
    verdict(metrics)


if __name__ == "__main__":
    main()
