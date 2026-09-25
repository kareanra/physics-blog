"""
Calculation of interference pattern for an electron passing through the double-slit apparatus.
"""

from __future__ import annotations

import numpy as np

# ---- constants (SI) ----
hbar = 1.054571817e-34
m_e = 9.1093837015e-31
q_e = 1.602176634e-19

# ---- default scenario: 1 keV electron, micron-scale optics ----
DEFAULTS = {
    "E_eV": 1.0e3,     # kinetic energy [eV]
    "L1": 0.10,        # source-to-slit drift [m]
    "L2": 0.50,        # slit-to-detection-screen distance [m]
    "a": 2.0e-6,       # inner-edge slit separation [m]
    "b": 1.0e-6,       # slit height [m]
    "sigma0": 1.0e-6,  # Gaussian beam waist at source [m]
    "m": m_e,
}


def derived_quantities(E_eV: float =DEFAULTS["E_eV"], L1: float =DEFAULTS["L1"],
                       sigma0: float =DEFAULTS["sigma0"], m: float =m_e) -> dict[str, float]:
    """Velocity, momentum, de Broglie wavelength, arrival time, spread at slits."""
    E = E_eV * q_e
    v = np.sqrt(2 * E / m)
    p = m * v
    lam = 2 * np.pi * hbar / p
    T1 = L1 / v
    sigmaT = np.sqrt(sigma0**2 + (hbar * T1 / (2 * m * sigma0))**2)
    return {"E": E, "v": v, "p": p, "lam": lam, "T1": T1, "sigmaT": sigmaT}


def slit_plane_alpha(T1, sigma0=DEFAULTS["sigma0"], m=m_e) -> :
    """Complex Gaussian width at the slit plane: alpha1 = sigma0^2 + i*hbar*T1/(2m)."""
    return sigma0**2 + 1j * hbar * T1 / (2 * m)


def psi_per_slit(yD, E_eV=DEFAULTS["E_eV"], L1=DEFAULTS["L1"], L2=DEFAULTS["L2"],
                      a=DEFAULTS["a"], b=DEFAULTS["b"], sigma0=DEFAULTS["sigma0"],
                      beta=None, m=m_e):
    """Closed-form screen amplitude from each slit (Gaussian slits)."""
    if beta is None:
        beta = b / np.sqrt(2 * np.pi)            # equal integrated transmission vs hard slit
    dd = derived_quantities(E_eV=E_eV, L1=L1, sigma0=sigma0, m=m)
    T1, v = dd["T1"], dd["v"]
    T2 = L2 / v
    alpha1 = slit_plane_alpha(T1, sigma0, m)
    y_s = (a + b) / 2.0
    lam2 = 1j * m / (2 * hbar * T2)
    Ac = 1.0 / (4 * alpha1) + 1.0 / (2 * beta**2)
    p = Ac - lam2

    def term(j):
        Bj = j * y_s / beta**2
        Qj = Bj - 2 * lam2 * yD
        return np.sqrt(np.pi / p) * np.exp(Qj**2 / (4 * p)) * np.exp(lam2 * yD**2)

    return term(+1), term(-1)


def screen_intensity(psi_p, psi_m):
    """Screen intensity on the detector as a function of y."""
    return (np.abs(psi_p)**2 + np.abs(psi_m)**2
            + 2 * np.real(psi_p * np.conj(psi_m)))


def draw_schematic(ax=None):
    """Draw the labeled double-slit geometry on a matplotlib axis (credit to Claude)."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.2))
    barrier_x, wall = 7.0, 0.28
    segs = [(1.5, 3.0), (-0.5, 0.5), (-3.0, -1.5)]         # upper wall, septum, lower wall
    for lo, hi in segs:
        ax.add_patch(Rectangle((barrier_x, lo), wall, hi - lo,
                               facecolor="#5F5E5A", edgecolor="none"))
    for yc in (1.0, -1.0):                                  # sample paths to each slit
        for dy in (-0.25, 0.25):
            ax.plot([0.5, barrier_x], [0.0, yc + dy], color="#BA7517",
                    lw=1, alpha=0.35, zorder=0)
    ax.plot(0.5, 0.0, "o", color="black", ms=7)
    ax.annotate("O (source)", (0.5, 0.0), (0.2, -0.55), fontsize=10, ha="left")
    ax.annotate("", (6.4, 0.0), (0.9, 0.0),
                arrowprops={"arrowstyle": "->", "color": "#888780", "lw": 1.2})
    ax.text(3.5, 0.16, "free particle, +x", color="#5F5E5A", fontsize=9, ha="center")
    ax.annotate("", (barrier_x - 0.15, -2.0), (0.5, -2.0),
                arrowprops={"arrowstyle": "<->", "color": "#444441", "lw": 1})
    ax.text((0.5 + barrier_x) / 2, -2.35, r"$L_1$", fontsize=12, ha="center")
    xr = barrier_x + wall + 0.15
    for (lo, hi, lab) in [(0.5, 1.5, "b"), (-0.5, 0.5, "a"), (-1.5, -0.5, "b")]:
        ax.annotate("", (xr, hi), (xr, lo),
                    arrowprops={"arrowstyle": "<->", "color": "#5F5E5A", "lw": 0.8})
        ax.text(xr + 0.18, (lo + hi) / 2, f"${lab}$", fontsize=12, va="center")
    ax.text(xr + 0.7, 1.0, "top slit", fontsize=9, va="center")
    ax.text(xr + 0.7, -1.0, "bottom slit", fontsize=9, va="center")
    ax.text(0.05, 1.9, r"$y=+a/2$", fontsize=8, ha="left", color="#5F5E5A")
    ax.set_xlim(-0.2, 10)
    ax.set_ylim(-3.2, 3.2)
    ax.axis("off")
    return ax
