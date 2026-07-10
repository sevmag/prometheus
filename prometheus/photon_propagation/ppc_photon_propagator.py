import glob
import logging
import os
import shutil
import subprocess

import numpy as np

from ..detector import Detector
from ..lepton_propagation import LeptonPropagator, Loss
from ..particle import Particle
from ..utils import serialize_to_f2k
from .photon_propagator import PhotonPropagator
from .utils import parse_ppc, should_propagate

logger = logging.getLogger(__name__)

# Collect subprocess statuses for run summaries
subprocess_statuses = []


def _dump_pmt_diag(diag_path: str, particle, om_conf_path: str) -> None:
    """Append per-hit and per-type diagnostics for the multi-PMT assignment bug.

    Gated by the ``PROM_PMT_DIAG`` env var (path to an append-only text file).
    Writes, per ``ppc_sim`` invocation:

    * the parsed per-OM-type PMT pointing directions from ``om.conf`` (to check
      the ``dirs`` are distinct / spread over the sphere), and
    * one line per hit: ``string om pmt_id pth pph dth dph`` where ``pth/pph`` is
      the PHOTON direction that drives ``getPMT`` selection (HIT tokens 5,6 in
      ``f2k.cxx:346``; stored as ``Hit.photon_zenith/photon_azimuth``) and
      ``dth/dph`` is the hit position on the OM (tokens 7,8; stored as
      ``Hit.om_zenith/om_azimuth``).

    Analyse with ``dir_z = cos(pth)`` (pth in radians -- the raw PPC angle units
    are unverified here: if |pth| ever exceeds ~pi it is degrees, convert first).
    A healthy detector exercises the full range of ``pth`` (hence many PMT
    indices) across DOMs at different positions relative to the cascade. A
    collapse onto ~1 PMT index means either ``pth`` is degenerate or the PMT
    frame is wrong -- not a ``dx.dat`` issue.
    """
    hits = getattr(particle, "hits", None) or []

    # Parse the PMT direction block(s) from om.conf (persists in the tmpdir).
    type_dirs = {}
    cur = None
    try:
        with open(om_conf_path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                toks = line.split()
                if not line[0].isspace():
                    # "type_<id> <id> area beta Rr Rz num <zen> <az> [cable]"
                    cur = toks[1]
                    type_dirs.setdefault(cur, []).append((float(toks[7]), float(toks[8])))
                elif cur is not None and len(toks) >= 2:
                    type_dirs[cur].append((float(toks[-2]), float(toks[-1])))
    except Exception as exc:  # diagnostics must never crash the sim
        logger.warning("PMT diag: could not parse %s: %s", om_conf_path, exc)

    with open(diag_path, "a") as out:
        out.write(f"# ppc_sim particle={particle} nhits={len(hits)}\n")
        for t, dirs in type_dirs.items():
            zens = [z for z, _ in dirs]
            ndist = len({(round(z, 3), round(a, 3)) for z, a in dirs})
            out.write(
                f"# type {t}: npmt={len(dirs)} ndistinct={ndist} "
                f"zen[min,max]=[{min(zens):.2f},{max(zens):.2f}]\n"
            )
        out.write(
            "# hits: string om pmt_id pth pph dth dph"
            "  (pth/pph=photon dir, dth/dph=pos on OM; raw PPC angle units)\n"
        )
        for h in hits:
            out.write(
                f"{h.string_id} {h.om_id} {h.pmt_id} "
                f"{h.photon_zenith:.4f} {h.photon_azimuth:.4f} "
                f"{h.om_zenith:.4f} {h.om_azimuth:.4f}\n"
            )


def ppc_sim(particle: Particle, det: Detector, lp: LeptonPropagator, ppc_config: dict) -> None:
    """Simulate the propagation of a particle and of any photons resulting from its energy losses.

    Parameters
    ----------
    particle : Particle
        Particle to propagate.
    det : Detector
        Detector object to simulate within.
    lp : LeptonPropagator
        Prometheus LeptonPropagator used to simulate any charged leptons.
    ppc_config : dict
        Dictionary containing the configuration settings for the photon
        propagation.
    """
    # TODO I think this could be factored out into a separate energy loss section
    # But that is not a now problem
    if abs(int(particle)) in [12, 14, 16]:  # It's a neutrino
        return
    # TODO put this in config
    r_inice = det.outer_radius + 1000
    if abs(int(particle)) in [11, 13, 15]:  # It's a charged lepton
        lp.energy_losses(particle, det)
    # All of these we consider as point depositions
    elif abs(int(particle)) in (211, 311, 321) or int(particle) == 111:  # pion or kaon
        # Point-deposit a pion or kaon. A particle and its antiparticle deposit
        # the same cascade light, so we normalise to the positive code with
        # abs(); the f2k cascade type then follows from int_type_to_str via
        # Loss.__str__:
        #   111 -> "epair" (EM cascade; pi0 -> gamma gamma)
        #   211 / 311 / 321 -> "hadr" (hadronic cascade)
        # pi0 is its own antiparticle, so only +111 is physical (a nonsense
        # -111 falls through to the else: raise below). Depositing here (instead
        # of the old early return) is the Issue #2 fix: it stops neutral-hadron
        # (pi0/K0) decay-product light from being silently dropped.
        if np.linalg.norm(particle.position - det.offset) <= r_inice:
            loss = Loss(abs(int(particle)), particle.e, particle.position)
            particle.losses.append(loss)
    elif int(particle) == -2000001006 or int(particle) == 2212:  # Hadrons
        if np.linalg.norm(particle.position - det.offset) <= r_inice:
            loss = Loss(int(particle), particle.e, particle.position)
            particle.losses.append(loss)
    else:
        # TODO make this into a custom error
        logger.error("Unrecognized particle: %r", particle)
        raise ValueError("Unrecognized particle")
    geo_tmpfile = f"{ppc_config['paths']['ppc_tmpdir']}/geo-f2k"
    ppc_tmpfile = (
        f"{ppc_config['paths']['ppc_tmpdir']}/{ppc_config['paths']['ppc_tmpfile']}_{str(particle)}"
    )
    f2k_tmpfile = (
        f"{ppc_config['paths']['ppc_tmpdir']}/{ppc_config['paths']['f2k_tmpfile']}_{str(particle)}"
    )
    command = (
        f"{ppc_config['paths']['ppc_exe']} {ppc_config['simulation']['device']}"
        f" < {f2k_tmpfile} > {ppc_tmpfile}"
    )
    # NOTE: stderr is intentionally NOT redirected to /dev/null here. It is
    # captured in Python below so a nonzero exit (bad --ppc-exe path, missing
    # tables, etc.) is raised instead of silently looking like "no photon hits".

    if not should_propagate(particle):
        return
    serialize_to_f2k(particle, f2k_tmpfile)
    det.to_f2k(geo_tmpfile, serial_nos=[m.serial_no for m in det.modules])

    ppc_tmpdir = ppc_config["paths"]["ppc_tmpdir"]

    if det.needs_nextgen():
        det.to_om_conf(os.path.join(ppc_tmpdir, "om.conf"))
        det.to_om_map(os.path.join(ppc_tmpdir, "om.map"))
        om_dirs_src = ppc_config["paths"].get("om_dirs", "")
        if not om_dirs_src:
            om_dirs_src = os.path.join(ppc_config["paths"]["ppctables"], "om.dirs")
        if os.path.exists(om_dirs_src):
            shutil.copy(om_dirs_src, os.path.join(ppc_tmpdir, "om.dirs"))
        else:
            logger.warning(
                "om.dirs not found at %s; PPC nextgen mode requires this file", om_dirs_src
            )
        # Stage the per-OM-type effective-area(QE)-vs-wavelength tables and the
        # eff-f2k table. PPC drops ALL hits for a nextgen OM type whose om.wv_*
        # file is missing, so these are mandatory in nextgen mode.
        for src in glob.glob(os.path.join(ppc_config["paths"]["ppctables"], "om.wv_*")):
            shutil.copy(src, os.path.join(ppc_tmpdir, os.path.basename(src)))
        eff = os.path.join(ppc_config["paths"]["ppctables"], "eff-f2k")
        if os.path.exists(eff):
            shutil.copy(eff, os.path.join(ppc_tmpdir, "eff-f2k"))
        # Stage per-DOM orientation inputs used by multi-PMT PMT assignment.
        # dx.dat = per-DOM cable azimuth -> sets getPMT()'s `ph` (>=0 enables the
        # per-DOM azimuthal rotation); cx.dat = per-DOM orientation vector. PPC
        # never sees these unless they are staged into the tmpdir, even if they
        # are present in ppctables.
        for fname in ("dx.dat", "cx.dat", "km3net_as.dat"):
            src = os.path.join(ppc_config["paths"]["ppctables"], fname)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(ppc_tmpdir, fname))

    tenv = os.environ.copy()
    tenv["PPCTABLESDIR"] = ppc_tmpdir
    # NEXTGENDIR defaults to PPCTABLESDIR in PPC, but since we stage tables into
    # a per-run tmpdir it must be pointed there explicitly for nextgen mode.
    tenv["NEXTGENDIR"] = ppc_tmpdir

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=tenv
    )
    # communicate() (not wait()) so the captured stderr pipe can't deadlock.
    _, stderr_data = process.communicate()
    rc = process.returncode
    subprocess_statuses.append({"cmd": command, "returncode": rc})
    stderr_text = (stderr_data or b"").decode("utf-8", "replace")
    if rc != 0:
        logger.error(
            "PPC exited with code %d for command %r\nstderr:\n%s", rc, command, stderr_text
        )
        raise RuntimeError(f"PPC failed with exit code {rc}; see logged stderr")
    if stderr_text and not ppc_config["simulation"]["supress_output"]:
        logger.info("PPC stderr:\n%s", stderr_text)

    particle.hits = parse_ppc(ppc_tmpfile)

    diag_path = os.environ.get("PROM_PMT_DIAG")
    if diag_path and det.needs_nextgen():
        _dump_pmt_diag(diag_path, particle, os.path.join(ppc_tmpdir, "om.conf"))
    for f in [geo_tmpfile, f2k_tmpfile, ppc_tmpfile]:
        os.remove(f)

    for child in particle.children:
        # TODO put this in config
        if child.e < 1:  # GeV
            continue
        ppc_sim(child, det, lp, ppc_config)


from .registry import register_propagator  # noqa: E402


@register_propagator("ppc")
@register_propagator("ppc_cuda")
class PPCPhotonPropagator(PhotonPropagator):
    """Interface for simulating energy losses and light propagation using ppc."""

    def propagate(self, particle: Particle, rng_key=None) -> None:
        """Propagate an input particle using ppc.

        This modifies the state of the input particle in-place.

        Parameters
        ----------
        particle : Particle
            Prometheus particle to propagate.
        rng_key : Any or None
            The parameter is ignored and accepted for interface compatibility; ppc uses its own internal RNG.
        """  # noqa: E501
        return ppc_sim(particle, self.detector, self.lepton_propagator, self.config)
