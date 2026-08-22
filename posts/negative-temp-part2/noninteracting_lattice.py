"""
noninteracting_lattice.py -- Entropy and energy calculations for an
ensemble of noninteracting spins in a magnetic field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from scipy.constants import k
from scipy.special import xlogy

if TYPE_CHECKING:
    from matplotlib.axes import Axes

# ---- N spins in a 2-D lattice in the presence of a magnetic field ----

N = 1000  # number of spins
MAGNETIC_MOMENT = 9.274e-24  # [J/T]
B_FIELD = 1.0  # [T]


def entropy(energy: NDArray[np.float64]) -> NDArray[np.floating[Any]]:
    """Entropy S(E) of n non-interacting spins of moment mu in a field b."""
    e_max = N * MAGNETIC_MOMENT * B_FIELD
    p_up = (e_max - energy) / (2 * e_max)
    p_down = (e_max + energy) / (2 * e_max)
    return -N * k * (xlogy(p_up, p_up) + xlogy(p_down, p_down))


def plot_entropy_vs_energy(ax: Axes | None = None) -> Axes:
    """Plot entropy as a function of energy."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.2))

    e_max = N * MAGNETIC_MOMENT * B_FIELD

    x = np.linspace(-4.0, 4.0, 40001)
    x = x[np.abs(x) > 1e-9]  # x = beta * mu * B
    energies = -e_max * np.tanh(x)
    entropies = entropy(energies)

    ax.plot(energies, entropies, lw=2, label="S(E), spin lattice")
    ax.set_xlabel("Energy E [J]")
    ax.set_ylabel("Entropy S [J/K]")
    ax.set_title("Entropy vs. Energy for noninteracting spins in a B field (T goes negative)")
    ax.legend()
    return ax
