#!/usr/bin/env python3
"""Build a multi-PMT ARCA Detector: arca.geo positions x the 31 canonical PMT dirs.

Every DOM in ``resources/geofiles/arca.geo`` (2070 of them) is turned into a
31-PMT nextgen module sharing a single ``module_type`` and the canonical
identity-orientation PMT pointing directions from
``resources/arca_dom_pmt_dirs.csv``.
"""

import os

import numpy as np

from prometheus.detector.detector import Detector
from prometheus.detector.detector_factory import read_medium
from prometheus.detector.module import Module

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.path.join(_REPO_ROOT, "resources", "geofiles", "arca.geo")
DIRS = os.path.join(_REPO_ROOT, "resources", "arca_dom_pmt_dirs.csv")


def _load_pmt_dirs(path=DIRS):
    """Return the 31 canonical (zenith_deg, azimuth_deg) PMT directions."""
    out = []
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln[0] == "#" or ln.lower().startswith("pmt"):
            continue
        _idx, zen, az = ln.split(",")
        out.append((float(zen), float(az)))
    assert len(out) == 31, f"expected 31 PMT dirs, got {len(out)}"
    return out


def build_arca_multipmt_detector(geo=GEO, module_type=1, Rr=0.2159, Rz=0.2159, beta=-3.0, area=5.53):
    """Build the 2070-DOM, 31-PMT-per-DOM ARCA nextgen detector.

    Parameters
    ----------
    geo : str
        Path to the ARCA geofile (positions + (string, om) keys).
    module_type : int
        Shared PPC om.conf type ID for every DOM. Must not be -1 so that the
        detector is flagged as nextgen.
    Rr, Rz : float
        Module semi-axes [m]. Default 0.2159 = 17" DOM sphere radius.
    beta : float
        PMT angular sensitivity shape parameter written to om.conf. The default
        -3.0 is a PPC sentinel selecting the tabulated measured KM3NeT per-PMT
        sensitivity (resources/PPC_tables/arca_water/km3net_as.dat) in nextgen
        multi-PMT mode. Pass beta=0.49 to fall back to the legacy analytic curve.
    area : float
        Overall light-collection scale written to om.conf, in PPC's internal
        units of one nominal IceCube DOM (pi*(0.1651 m)^2 x 0.336 average
        angular sensitivity, about 287 cm^2). The default 5.53 is the measured
        ARCA value: it closes PPC cascade yields against a first-principles
        expectation (Frank-Tamm x KM3NeT absorption x om.wv_1.0 x real PMT
        directions) to 1.00 +- 3% across 100 GeV-1 TeV and 10-20 m, and agrees
        with the photocathode-area ratio 31 x 45 cm^2 / 287 cm^2 = 4.85 to
        ~15%. Derivation and toys: prometheus-docs yield-check ANCHOR_RESULTS.

    Returns
    -------
    Detector
        Prometheus detector with one nextgen module per DOM.
    """
    pmt_dirs = _load_pmt_dirs()
    medium = read_medium(geo)
    lines = open(geo).readlines()
    start = lines.index("### Modules ###\n") + 1
    modules = []
    for ln in lines[start:]:
        c = ln.strip("\n").split("\t")
        if len(c) < 5:
            continue
        pos = np.array([float(c[0]), float(c[1]), float(c[2])])
        key = (int(c[3]), int(c[4]))
        modules.append(
            Module(
                pos,
                key,
                module_type=module_type,
                Rr=Rr,
                Rz=Rz,
                beta=beta,
                area=area,
                n_pmts=31,
                pmt_dirs=list(pmt_dirs),
            )
        )
    return Detector(modules, medium)


if __name__ == "__main__":
    det = build_arca_multipmt_detector()
    print(f"built ARCA detector: {len(det.modules)} DOMs, needs_nextgen={det.needs_nextgen()}")
