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
from prometheus.detector.detector_factory import (
    read_dom_radius,
    read_dom_vertical_radius,
    read_medium,
)
from prometheus.detector.module import Module

PR = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
GEO = os.path.join(PR, "resources", "geofiles", "arca.geo")
DIRS = os.path.join(PR, "resources", "arca_dom_pmt_dirs.csv")


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


def build_arca_multipmt_detector(
    geo=GEO, module_type=1, Rr=None, Rz=None, beta=0.49, area=1.0
):
    """Build the 2070-DOM, 31-PMT-per-DOM ARCA nextgen detector.

    Parameters
    ----------
    geo : str
        Path to the ARCA geofile (positions + (string, om) keys).
    module_type : int
        Shared PPC om.conf type ID for every DOM. Must not be -1 so that the
        detector is flagged as nextgen.
    Rr, Rz : float, optional
        Module semi-axes [m]. Default: read from the geofile's ``DOM Radius``
        (Rr) and optional ``DOM Vertical Radius`` (Rz) headers. A missing vertical
        radius means a sphere (Rz = Rr); a missing DOM Radius falls back to
        0.2159 m (17" DOM sphere). An explicit argument overrides the geofile.
    beta : float
        PMT angular sensitivity shape parameter.
    area : float
        Overall efficiency scaling factor written to om.conf.

    Returns
    -------
    Detector
        Prometheus detector with one nextgen module per DOM.
    """
    pmt_dirs = _load_pmt_dirs()
    medium = read_medium(geo)
    if Rr is None or Rz is None:
        geo_rr = read_dom_radius(geo)
        if geo_rr is None:
            geo_rr = 0.2159  # 17" KM3NeT DOM sphere
        geo_rz = read_dom_vertical_radius(geo)
        if geo_rz is None:
            geo_rz = geo_rr  # no vertical radius in header -> sphere
        Rr = geo_rr if Rr is None else Rr
        Rz = geo_rz if Rz is None else Rz
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
    print(
        f"built ARCA detector: {len(det.modules)} DOMs, "
        f"needs_nextgen={det.needs_nextgen()}"
    )
