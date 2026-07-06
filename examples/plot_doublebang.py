#!/usr/bin/env python3
"""Multi-PMT ARCA 10 PeV nu_tau in water: 3D double-bang + a multi-PMT DOM view.
Left  : every PMT-with-hits as a circle at its DOM position; size ~ log10(hits/PMT),
        color ~ earliest hit time (red=earlier, violet=later) -> tau double-bang.
Right : the busiest DOM's 31 PMTs on a sphere, showing WHICH PMTs fired and when
        (the directional multi-PMT information)."""
import glob, os, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PR = "/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus"
# newest by mtime (not alphabetical glob[-1], which can grab a stale run)
df = pd.read_parquet(max(glob.glob(PR + "/output/arca_multipmt_tau/*_photons.parquet"),
                         key=os.path.getmtime))
ZMIN, ZMAX, RXY = -3500.0, -2888.0, 500.0

def hits(i):
    p = df["photons"].iloc[i]
    # pmt_id is the real PMT index (0-30). NB: id_idx is NOT the PMT -- it is the
    # producing particle's serialization index; using it here was the original bug.
    return tuple(np.asarray(p[k]) for k in
                 ("sensor_pos_x","sensor_pos_y","sensor_pos_z","t","string_id","sensor_id","pmt_id"))
def inside(pt): return (ZMIN-50 < pt[2] < ZMAX+50) and abs(pt[0]) < RXY+50 and abs(pt[1]) < RXY+50

# ---- select the clearest contained double-bang ----
best_i, best_score, meta = None, -1e9, None
for i in range(len(df)):
    if not len(df["photons"].iloc[i]["t"]): continue
    mt = df["mc_truth"].iloc[i]
    v = np.array([mt["initial_state_x"], mt["initial_state_y"], mt["initial_state_z"]])
    F = np.stack([np.atleast_1d(mt["final_state_x"]), np.atleast_1d(mt["final_state_y"]), np.atleast_1d(mt["final_state_z"])], 1)
    far = F[np.linalg.norm(F - v, axis=1) > 100]
    if len(far) == 0 or not inside(v): continue
    c2 = far.mean(0); sep = np.linalg.norm(c2 - v)
    x,y,z,t = hits(i)[:4]; ph = np.stack([x,y,z],1)
    n1 = int((np.linalg.norm(ph-v,axis=1) < 110).sum()); n2 = int((np.linalg.norm(ph-c2,axis=1) < 110).sum())
    if not (n1 > 80 and n2 > 30 and 200 < sep < 520): continue
    score = -abs(sep - 330)
    if score > best_score: best_i, best_score, meta = i, score, (v, c2, sep, n1, n2, len(t))
if best_i is None:
    best_i = max(range(len(df)), key=lambda i: len(df["photons"].iloc[i]["t"]))
    mt = df["mc_truth"].iloc[best_i]; v = np.array([mt["initial_state_x"],mt["initial_state_y"],mt["initial_state_z"]])
    F = np.stack([np.atleast_1d(mt["final_state_x"]),np.atleast_1d(mt["final_state_y"]),np.atleast_1d(mt["final_state_z"])],1)
    c2 = F[int(np.argmax(np.linalg.norm(F-v,axis=1)))]; meta = (v,c2,np.linalg.norm(c2-v),0,0,len(df["photons"].iloc[best_i]["t"]))
    print("no clean contained double-bang; using max-hit event", best_i)
v, c2, sep, n1, n2, nhit = meta
print(f"selected event {best_i}: {nhit} hits; sep={sep:.0f} m; c1_hits={n1}, c2_hits={n2}")

x,y,z,t,st,om,pm = hits(best_i)
fig = plt.figure(figsize=(20, 9))

# ---- LEFT: full-detector double-bang (per-PMT circles) ----
key = st.astype(np.int64)*100000 + om.astype(np.int64)*100 + pm.astype(np.int64)
uk, inv = np.unique(key, return_inverse=True); nP = len(uk)
cnt = np.zeros(nP); px = np.zeros(nP); py = np.zeros(nP); pz = np.zeros(nP)
np.add.at(cnt,inv,1.0); np.add.at(px,inv,x); np.add.at(py,inv,y); np.add.at(pz,inv,z)
pte = np.full(nP, np.inf); np.minimum.at(pte, inv, t); px/=cnt; py/=cnt; pz/=cnt
order = np.argsort(-pte)
ax = fig.add_subplot(121, projection="3d")
sc = ax.scatter(px[order],py[order],pz[order], s=6+60*np.log10(cnt+1)/np.log10(cnt.max()+1),
                c=pte[order], cmap="rainbow_r", alpha=0.9, edgecolors="none")
fig.colorbar(sc, ax=ax, pad=0.02, shrink=0.55).set_label("earliest hit time [ns] (red=earlier, violet=later)")
ax.scatter(*v, marker="*", s=420, c="k", label="$\\nu_\\tau$ vertex (cascade 1)")
ax.scatter(*c2, marker="X", s=320, c="dimgray", label=f"$\\tau$ decay (cascade 2, {sep:.0f} m)")
ax.plot([v[0],c2[0]],[v[1],c2[1]],[v[2],c2[2]], "k--", lw=1, alpha=0.6)
ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
ax.set_title(f"ARCA multi-PMT 10 PeV $\\nu_\\tau$ CC in water (event {best_i}, {nhit} hits, {nP} PMTs)\ncircle size $\\propto\\log_{{10}}$(hits/PMT); tau double-bang")
ax.legend(loc="upper left", fontsize=9); ax.view_init(elev=12, azim=np.degrees(np.arctan2(c2[1]-v[1], c2[0]-v[0]))+90)

# ---- RIGHT: multi-PMT view of the busiest DOM ----
pdirs = {}
for ln in open(PR + "/resources/arca_dom_pmt_dirs.csv"):
    ln = ln.strip()
    if not ln or ln[0]=="#" or ln.lower().startswith("pmt"): continue
    idx, zen, az = ln.split(","); pdirs[int(float(idx))] = (float(zen), float(az))
kd = st.astype(np.int64)*100000 + om.astype(np.int64)*100
ud, cd = np.unique(kd, return_counts=True); busy = ud[np.argmax(cd)]; mb = kd == busy
b_st, b_om = int(busy//100000), int(busy%100000//100)
dom_pos = np.array([x[mb][0], y[mb][0], z[mb][0]])
b_pm = pm[mb].astype(int); b_t = t[mb]
ups, pinv = np.unique(b_pm, return_inverse=True)
pcnt = np.zeros(len(ups)); np.add.at(pcnt, pinv, 1.0)
pemin = np.full(len(ups), np.inf); np.minimum.at(pemin, pinv, b_t)
hm = {int(u): (pcnt[j], pemin[j]) for j,u in enumerate(ups)}
ax2 = fig.add_subplot(122, projection="3d")
for idx,(zen,az) in pdirs.items():
    zr, ar = np.radians(zen), np.radians(az)
    P = np.array([np.sin(zr)*np.cos(ar), np.sin(zr)*np.sin(ar), np.cos(zr)])
    if idx in hm:
        cc, tt = hm[idx]
        ax2.scatter(*P, s=40+160*np.log10(cc+1)/np.log10(pcnt.max()+1), c=[tt],
                    cmap="rainbow_r", vmin=b_t.min(), vmax=b_t.max(), edgecolors="k", zorder=5)
    else:
        ax2.scatter(*P, s=22, c="lightgray", edgecolors="gray", zorder=1)
# arrows from DOM center toward each cascade (directionality)
for tgt, col, lab in [(v,"k","-> cascade 1"), (c2,"dimgray","-> cascade 2")]:
    d = tgt - dom_pos; d = d/np.linalg.norm(d)
    ax2.quiver(0,0,0, d[0],d[1],d[2], length=1.25, color=col, lw=2, arrow_length_ratio=0.12)
ax2.set_title(f"multi-PMT view: DOM (string {b_st}, om {b_om}) — {len(ups)}/31 PMTs hit\n"
              "gray=no hit; size $\\propto\\log_{10}$(hits); color=time; arrows toward the two cascades")
ax2.set_xlabel("x"); ax2.set_ylabel("y"); ax2.set_zlabel("z (up)")
for s in (ax2.set_xlim,ax2.set_ylim,ax2.set_zlim): s(-1.3,1.3)
fig.tight_layout()
out = PR + "/output/arca_multipmt_tau/doublebang.png"
fig.savefig(out, dpi=135, bbox_inches="tight"); print("saved", out)
