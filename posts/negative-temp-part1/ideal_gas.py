"""
ideal_gas.py -- Sackur-Tetrode entropy of a monatomic ideal gas,
used to illustrate positive temperature at every entropy and energy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np
from numpy.typing import NDArray
from scipy.constants import h, k

if TYPE_CHECKING:
    from matplotlib.axes import Axes

FloatArray = NDArray[np.float64]

# ---- toy system: N particles of helium-4 in a fixed volume ----
DEFAULTS = {
    "N": 1000,              # particle count
    "V": 1.0e-3,            # volume [m^3]
    "m": 6.6464731e-27,     # He-4 atomic mass [kg]
}


@overload
def entropy(energy: float, n: float = ..., v: float = ..., m: float = ...) -> np.float64: ...
@overload
def entropy(energy: FloatArray, n: float = ..., v: float = ..., m: float = ...) -> FloatArray: ...


def entropy(energy: float | FloatArray,
            n: float = DEFAULTS["N"],
            v: float = DEFAULTS["V"],
            m: float = DEFAULTS["m"]) -> np.float64 | FloatArray:
    """Sackur-Tetrode entropy S(E) of a monatomic ideal gas at fixed N, V."""
    return n * k * (np.log((v / n) * (4 * np.pi * m * energy / (3 * n * h ** 2)) ** 1.5) + 2.5)


@overload
def energy_of_temperature(t: float, n: float = ...) -> float: ...
@overload
def energy_of_temperature(t: FloatArray, n: float = ...) -> FloatArray: ...


def energy_of_temperature(t: float | FloatArray, n: float = DEFAULTS["N"]) -> float | FloatArray:
    """Mean internal energy of a monatomic ideal gas: E = (3/2) N k_B T."""
    return 1.5 * n * k * t


def draw_entropy_vs_energy(ax: Axes | None = None,
                           temp_highlighted: float = 300.0,
                           T_min: float = 50.0,
                           T_max: float = 800.0) -> Axes:
    """Plot S(E) with the tangent dS/dE = 1/T marked at temp_highlighted."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.2))

    temperatures = np.linspace(T_min, T_max, 400)
    energies = energy_of_temperature(temperatures)
    entropies = entropy(energies)

    energy_highlighted = energy_of_temperature(temp_highlighted)
    entropy_highlighted = entropy(energy_highlighted)
    slope = 1.0 / temp_highlighted                      # dS/dE = 1/T

    dE = 0.15 * (np.max(energies) - np.min(energies))
    energy_tangent = np.array([energy_highlighted - dE, energy_highlighted + dE])
    S_tangent = entropy_highlighted + slope * (energy_tangent - energy_highlighted)

    ax.plot(energies, entropies, lw=2, label="S(E), ideal gas")
    ax.plot(energy_tangent, S_tangent, "--", color="firebrick", lw=1.5,
            label=f"tangent at T = {temp_highlighted:.0f} K,  slope = 1/T > 0")
    ax.plot(energy_highlighted, entropy_highlighted, "o", color="firebrick")
    ax.annotate(f"T = {temp_highlighted:.0f} K", (energy_highlighted, entropy_highlighted), xytext=(12, -20),
                textcoords="offset points", color="firebrick")
    ax.set_xlabel("Energy E [J]")
    ax.set_ylabel("Entropy S [J/K]")
    ax.set_title("Ideal gas: entropy always increases with energy (T > 0 everywhere)")
    ax.legend()
    return ax


if __name__ == "__main__":
    T = np.linspace(50.0, 800.0, 400)
    E = energy_of_temperature(T)
    numeric = np.gradient(entropy(E), E)
    analytic = 1.0 / T
    worst = np.max(np.abs(numeric - analytic) / analytic)
    # Sanity checks
    print(f"dS/dE vs 1/T: worst relative error = {worst:.4%}")
    print(f"dS/dE > 0 across the whole range: {bool((numeric > 0).all())}")
