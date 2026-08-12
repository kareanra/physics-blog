"""
dslit.py — free-particle path-integral double slit, consolidated.

Single importable module behind the blog series. It merges the three working
scripts (kernel/transmission, detection screen, decoherence) into one clean API
so every post can `import dslit` and regenerate its figures at render time.

Physics summary
---------------
Free-particle kernel from the path integral:
    K(y,T;y0,0) = sqrt(m / (2*pi*i*hbar*T)) * exp( i*m*(y-y0)^2 / (2*hbar*T) )
The transverse (y) motion carries the interference; the x-motion is free drift
that only sets the arrival time T1 = L1/v, with v = sqrt(2E/m).
"""

from __future__ import annotations
import numpy as np
from scipy.special import erf
from scipy.integrate import quad

# numpy 2.0 renamed trapz -> trapezoid; support both
_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

# ---- constants (SI) ----
hbar = 1.054571817e-34
m_e = 9.1093837015e-31
q_e = 1.602176634e-19

# ---- default scenario: 1 keV electron, micron-scale optics ----
DEFAULTS = dict(
    E_eV=1.0e3,     # kinetic energy [eV]
    L1=0.10,        # source-to-slit drift [m]
    L2=0.50,        # slit-to-detection-screen distance [m]
    a=2.0e-6,       # inner-edge slit separation [m]
    b=1.0e-6,       # slit height [m]
    sigma0=1.0e-6,  # Gaussian beam waist at source [m]
    m=m_e,
)


def derived_quantities(E_eV=DEFAULTS["E_eV"], L1=DEFAULTS["L1"],
                       sigma0=DEFAULTS["sigma0"], m=m_e):
    """Velocity, momentum, de Broglie wavelength, arrival time, spread at slits."""
    E = E_eV * q_e
    v = np.sqrt(2 * E / m)
    p = m * v
    lam = 2 * np.pi * hbar / p
    T1 = L1 / v
    sigmaT = np.sqrt(sigma0**2 + (hbar * T1 / (2 * m * sigma0))**2)
    return dict(E=E, v=v, p=p, lam=lam, T1=T1, sigmaT=sigmaT)


def slit_plane_alpha(T1, sigma0=DEFAULTS["sigma0"], m=m_e):
    """Complex Gaussian width at the slit plane: alpha1 = sigma0^2 + i*hbar*T1/(2m)."""
    return sigma0**2 + 1j * hbar * T1 / (2 * m)


# ---------------------------------------------------------------------------
# Transmission through either slit
# ---------------------------------------------------------------------------
def P_closed_form(a=DEFAULTS["a"], b=DEFAULTS["b"], sigmaT=None, **kw):
    """Closed-form transmission through either slit (erf), both slits by symmetry."""
    if sigmaT is None:
        sigmaT = derived_quantities(**kw)["sigmaT"]
    s = np.sqrt(2) * sigmaT
    return erf((a / 2 + b) / s) - erf((a / 2) / s)


def P_quadrature(a=DEFAULTS["a"], b=DEFAULTS["b"], sigmaT=None, **kw):
    """Same transmission by numerical quadrature of |psi|^2 over the openings."""
    if sigmaT is None:
        sigmaT = derived_quantities(**kw)["sigmaT"]
    dens = lambda y: np.exp(-y**2 / (2 * sigmaT**2)) / (np.sqrt(2 * np.pi) * sigmaT)
    top, _ = quad(dens, a / 2, a / 2 + b)
    bot, _ = quad(dens, -a / 2 - b, -a / 2)
    return top + bot


def propagate_via_kernel(y_eval, T1, sigma0=DEFAULTS["sigma0"], m=m_e,
                         y0_max=8e-6, N0=16001):
    """psi(y,T1) = integral dy0 K(y,T1;y0,0) psi0(y0): direct Fresnel convolution."""
    y0 = np.linspace(-y0_max, y0_max, N0)
    psi0 = (1.0 / (2 * np.pi * sigma0**2))**0.25 * np.exp(-y0**2 / (4 * sigma0**2))
    pref = np.sqrt(m / (2j * np.pi * hbar * T1))
    psi = np.empty(len(y_eval), dtype=complex)
    for i, y in enumerate(y_eval):
        ker = pref * np.exp(1j * m * (y - y0)**2 / (2 * hbar * T1))
        psi[i] = _trapz(ker * psi0, y0)
    return psi


# ---------------------------------------------------------------------------
# Detection screen (per-slit amplitudes for both models)
# ---------------------------------------------------------------------------
def per_slit_analytic(yD, E_eV=DEFAULTS["E_eV"], L1=DEFAULTS["L1"], L2=DEFAULTS["L2"],
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


def per_slit_numeric(yD, E_eV=DEFAULTS["E_eV"], L1=DEFAULTS["L1"], L2=DEFAULTS["L2"],
                     a=DEFAULTS["a"], b=DEFAULTS["b"], sigma0=DEFAULTS["sigma0"],
                     m=m_e, n_per_slit=4000):
    """Hard-slit screen amplitude from each slit (Fresnel quadrature)."""
    dd = derived_quantities(E_eV=E_eV, L1=L1, sigma0=sigma0, m=m)
    T1, v = dd["T1"], dd["v"]
    T2 = L2 / v
    alpha1 = slit_plane_alpha(T1, sigma0, m)
    pref = np.sqrt(m / (2j * np.pi * hbar * T2))

    def hop(y):
        psi1 = np.exp(-y**2 / (4 * alpha1))
        dy = y[1] - y[0]
        phase = 1j * m * (yD[:, None] - y[None, :])**2 / (2 * hbar * T2)
        return pref * np.sum(np.exp(phase) * psi1[None, :], axis=1) * dy

    ytop = np.linspace(a / 2, a / 2 + b, n_per_slit)
    ybot = np.linspace(-a / 2 - b, -a / 2, n_per_slit)
    return hop(ytop), hop(ybot)


def screen_intensity(psi_p, psi_m, mu=1.0):
    """Screen intensity with a which-path coherence factor mu in [0,1] on the cross term."""
    return (np.abs(psi_p)**2 + np.abs(psi_m)**2
            + 2 * np.real(mu * psi_p * np.conj(psi_m)))


def fringe_spacing(E_eV=DEFAULTS["E_eV"], L2=DEFAULTS["L2"],
                   a=DEFAULTS["a"], b=DEFAULTS["b"], L1=DEFAULTS["L1"],
                   sigma0=DEFAULTS["sigma0"], m=m_e):
    """Far-field fringe spacing lambda*L2/(a+b) and single-slit envelope first zero."""
    lam = derived_quantities(E_eV=E_eV, L1=L1, sigma0=sigma0, m=m)["lam"]
    return lam * L2 / (a + b), lam * L2 / b


# ---------------------------------------------------------------------------
# Which-path decoherence
# ---------------------------------------------------------------------------
def visibility(yD, psi_p, psi_m, mu, d=None, E_eV=DEFAULTS["E_eV"], L2=DEFAULTS["L2"]):
    """Central-fringe visibility relative to the local mean; equals |mu| for equal slits."""
    if d is None:
        d = DEFAULTS["a"] + DEFAULTS["b"]
    lam = derived_quantities(E_eV=E_eV)["lam"]
    fr = lam * L2 / d
    B = np.abs(psi_p)**2 + np.abs(psi_m)**2
    R = screen_intensity(psi_p, psi_m, mu) / B
    win = np.abs(yD) <= 0.6 * fr
    Rw = R[win]
    return (Rw.max() - Rw.min()) / (Rw.max() + Rw.min())


def mu_scattering(lambda_p, d=None):
    """Single-photon which-path overlap sinc(k_p d), k_p = 2*pi/lambda_p."""
    if d is None:
        d = DEFAULTS["a"] + DEFAULTS["b"]
    x = (2 * np.pi / lambda_p) * d
    return np.sin(x) / x


# ---------------------------------------------------------------------------
# Schematic (matplotlib) so the setup figure is reproducible too
# ---------------------------------------------------------------------------
def draw_schematic(ax=None):
    """Draw the labeled double-slit geometry on a matplotlib axis."""
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
                arrowprops=dict(arrowstyle="->", color="#888780", lw=1.2))
    ax.text(3.5, 0.16, "free particle, +x", color="#5F5E5A", fontsize=9, ha="center")
    ax.annotate("", (barrier_x - 0.15, -2.0), (0.5, -2.0),
                arrowprops=dict(arrowstyle="<->", color="#444441", lw=1))
    ax.text((0.5 + barrier_x) / 2, -2.35, r"$L_1$", fontsize=12, ha="center")
    xr = barrier_x + wall + 0.15
    for (lo, hi, lab) in [(0.5, 1.5, "b"), (-0.5, 0.5, "a"), (-1.5, -0.5, "b")]:
        ax.annotate("", (xr, hi), (xr, lo),
                    arrowprops=dict(arrowstyle="<->", color="#5F5E5A", lw=0.8))
        ax.text(xr + 0.18, (lo + hi) / 2, f"${lab}$", fontsize=12, va="center")
    ax.text(xr + 0.7, 1.0, "top slit", fontsize=9, va="center")
    ax.text(xr + 0.7, -1.0, "bottom slit", fontsize=9, va="center")
    ax.text(0.05, 1.9, r"$y=+a/2$", fontsize=8, ha="left", color="#5F5E5A")
    ax.set_xlim(-0.2, 10)
    ax.set_ylim(-3.2, 3.2)
    ax.axis("off")
    return ax


if __name__ == "__main__":
    d = derived_quantities()
    print(f"de Broglie = {d['lam']*1e12:.3f} pm, sigma(T1) = {d['sigmaT']*1e6:.3f} um")
    print(f"P(either slit): closed form = {P_closed_form():.6f}, "
          f"quadrature = {P_quadrature():.6f}")
    fr, env = fringe_spacing()
    print(f"fringe spacing = {fr*1e6:.3f} um, envelope zero = {env*1e6:.3f} um")
