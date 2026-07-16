"""PPC_NEXTGEN must consume TR angles as radians of the travel direction.

Prometheus's f2k writer emits theta/phi in radians (utils/write_to_f2k.py), so
the stock f2000 degrees + origin-flip conversion has to stay disabled in the
nextgen f2k parser, as it is in the legacy PPC/PPC_CUDA builds. If the
conversion is re-enabled, every cascade emits its light along a fixed
near-vertical axis regardless of the true direction, and the directional
asymmetries asserted here vanish.

Runs the actual CPU binary against the shipped arca_water tables with a
2-DOM-per-axis toy geometry; skipped when the binary is not present/executable.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PPC = REPO / "resources" / "PPC_executables" / "PPC_NEXTGEN" / "ppc"
TABLES = REPO / "resources" / "PPC_tables" / "arca_water"

GEO = """0x1\t0x1\t50.0\t0.0\t-3000.0\t1\t1
0x2\t0x2\t-50.0\t0.0\t-3000.0\t2\t1
0x5\t0x5\t0.0\t0.0\t-2950.0\t5\t1
0x6\t0x6\t0.0\t0.0\t-3050.0\t6\t1
"""

# 20 TeV EM cascade at surface-referenced z = -3000 m; the writer convention
# adds PPC_MAGIC_Z = 1948.07 to source z, hence -1051.93 in the TR line.
F2K = (
    "EM 0 1 0 0 0 0 \n"
    "MC E 20000 x 0 y 0 z -1051.93 theta {th} phi {ph}\n"
    "TR 0 0 epair 0.0 0.0 -1051.93 {th} {ph} 0 20000 0 \n"
    "EE\n"
)


def _hits_per_string(tabledir: Path, theta: float, phi: float) -> dict:
    env = dict(os.environ, PPCTABLESDIR=f"{tabledir}/", NEXTGENDIR=f"{tabledir}/")
    out = subprocess.run(
        [str(PPC), "0"],
        input=F2K.format(th=theta, ph=phi),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    hits = {}
    for line in out.stdout.splitlines():
        tok = line.split()
        if tok and tok[0] == "HIT":
            hits[int(tok[1])] = hits.get(int(tok[1]), 0) + 1
    return hits


@pytest.fixture(scope="module")
def tabledir(tmp_path_factory):
    if not (PPC.exists() and os.access(PPC, os.X_OK)):
        pytest.skip("PPC_NEXTGEN CPU binary not available")
    d = tmp_path_factory.mktemp("ppctables")
    for f in TABLES.iterdir():
        if f.name != "eff-f2k":  # DeepCore rde list would blind unrelated DOMs
            shutil.copy(f, d)
    (d / "geo-f2k").write_text(GEO)
    return d


def test_horizontal_direction_discrimination(tabledir):
    px = _hits_per_string(tabledir, 1.5707963, 0.0)
    mx = _hits_per_string(tabledir, 1.5707963, 3.1415927)
    # Travel +x must strongly favor the +x DOM (string 1) and vice versa.
    assert px.get(1, 0) > 3 * (px.get(2, 0) + 1)
    assert mx.get(2, 0) > 3 * (mx.get(1, 0) + 1)


def test_vertical_direction_discrimination(tabledir):
    up = _hits_per_string(tabledir, 0.0, 0.0)
    # Travel up must strongly favor the DOM above the vertex (string 5).
    assert up.get(5, 0) > 3 * (up.get(6, 0) + 1)
