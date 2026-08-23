"""
noninteracting_lattice.py -- Microcanonical treatment of N noninteracting
spins in a magnetic field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from scipy.constants import k
from scipy.special import gammaln, xlogy

if TYPE_CHECKING:
    from matplotlib.axes import Axes

# ---- N spins in a 2-D lattice in the presence of a magnetic field ----

N = 1000  # number of spins
MAGNETIC_MOMENT = 9.274e-24  # [J/T]
B_FIELD = 1.0  # [T]

E_MAX = N * MAGNETIC_MOMENT * B_FIELD  # fully anti-aligned; ground state is -E_MAX


def macrostates() -> NDArray[np.int64]:
    """The N+1 accessible macrostates."""
    return np.arange(N + 1)


def energy_levels(n_up: NDArray[np.int64]) -> NDArray[np.floating[Any]]:
    """E = -mu B (N_up - N_down)."""
    return -MAGNETIC_MOMENT * B_FIELD * (2.0 * n_up - N)


def multiplicity_log(n_up: NDArray[np.int64]) -> NDArray[np.floating[Any]]:
    """ln Omega = ln C(N, N_up), evaluated exactly via log-gamma."""
    return gammaln(N + 1) - gammaln(n_up + 1) - gammaln(N - n_up + 1)


def entropy(n_up: NDArray[np.int64]) -> NDArray[np.floating[Any]]:
    """S = k ln Omega: the Boltzmann entropy, counted exactly."""
    return k * multiplicity_log(n_up)


def entropy_stirling(energy: NDArray[np.floating[Any]]) -> NDArray[np.floating[Any]]:
    """Computed with Stirling's approximation.

    S(E) = -N k [ f ln f + (1-f) ln(1-f) ],  f = (E_MAX - E) / (2 E_MAX)
    """
    f_up = (E_MAX - energy) / (2 * E_MAX)
    f_down = (E_MAX + energy) / (2 * E_MAX)
    return -N * k * (xlogy(f_up, f_up) + xlogy(f_down, f_down))


def inverse_temperature(n_up: NDArray[np.int64]) -> NDArray[np.floating[Any]]:
    """1/T = dS/dE, the microcanonical definition of temperature."""
    return np.gradient(entropy(n_up), energy_levels(n_up))


def temperature(n_up: NDArray[np.int64]) -> NDArray[np.floating[Any]]:
    """T = (dS/dE)^-1."""
    with np.errstate(divide="ignore"):
        return 1.0 / inverse_temperature(n_up)


def plot_entropy_vs_energy(ax: Axes | None = None) -> Axes:
    """Plot entropy as a function of energy, exact count vs the Stirling form."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.2))

    n_up = macrostates()
    energies = energy_levels(n_up)

    ax.plot(energies, entropy(n_up), lw=2, label=r"$S = k_B \ln \Omega(E)$ (exact count)")
    ax.plot(energies, entropy_stirling(energies), "--", lw=1.5, color="firebrick",
            label="Stirling closed form")
    ax.set_xlabel("Energy E [J]")
    ax.set_ylabel("Entropy S [J/K]")
    ax.set_title("Entropy vs. Energy for noninteracting spins in a B field (T goes negative)")
    ax.legend()
    return ax


def plot_inverse_temperature_vs_energy(ax: Axes | None = None) -> Axes:
    """Plot 1/T against energy, showing the sign change at E = 0."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.2))

    n_up = macrostates()
    energies = energy_levels(n_up)

    ax.plot(energies, inverse_temperature(n_up), lw=2)
    ax.axhline(0.0, color="0.6", lw=0.8)
    ax.axvline(0.0, color="0.6", lw=0.8)
    ax.set_xlabel("Energy E [J]")
    ax.set_ylabel(r"$1/T = dS/dE$  [1/K]")
    ax.set_title("Inverse temperature crosses zero (T is negative above E = 0)")
    return ax


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    n_up = macrostates()
    energies = energy_levels(n_up)
    entropies = entropy(n_up)

    print(f"{N + 1} energy levels from {energies.min():.3e} to {energies.max():.3e} J, "
          f"spaced by {2 * MAGNETIC_MOMENT * B_FIELD:.3e} J")
    print(f"S peaks at E = {energies[entropies.argmax()]:+.3e} J: "
          f"{entropies.max():.6e} vs N k ln2 = {N * k * np.log(2):.6e} J/K")
    print(f"endpoints (Omega = 1): S = {entropies[0]:.3e}, {entropies[-1]:.3e} J/K")

    worst = np.max(np.abs(entropy_stirling(energies) - entropies)[1:-1] / entropies[1:-1])
    print(f"Stirling closed form vs exact count: worst relative error = {worst:.3%}")

    temps = temperature(n_up)
    below, above = energies < 0, energies > 0
    print(f"T > 0 everywhere below E = 0: {bool((temps[below] > 0).all())}")
    print(f"T < 0 everywhere above E = 0: {bool((temps[above] < 0).all())}")
    print(f"at the peak (E = 0): 1/T = {inverse_temperature(n_up)[N // 2]:.3e}, "
          f"T = {temps[N // 2]}")

    plot_entropy_vs_energy()
    plot_inverse_temperature_vs_energy()
    plt.show()
