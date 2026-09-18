"""
metropolis_mc.py -- Metropolis Monte Carlo for the 2-D Ising model on a square
lattice with periodic boundary conditions and no external field.

Units: J = 1 and k_B = 1 throughout, so energies are in units of J, inverse
temperatures beta in 1/J, and entropies in k_B.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray
from scipy.integrate import cumulative_trapezoid

if TYPE_CHECKING:
    from matplotlib.axes import Axes

LATTICE_SIZE = 50
SEED = 42

# One sweep = one attempted flip per site. Single-spin-flip dynamics needs many
# sweeps to forget the random starting configuration, so measurement only
# begins after the burn-in is done.
BURN_IN_SWEEPS = 200
MEASURE_SWEEPS = 200

# The sweep has to straddle beta = 0, and has to land on it exactly: that is
# the reference point the entropy integration is anchored to.
BETAS = np.linspace(-1.0, 1.0, 201)

# Onsager's exact critical point for this model, beta_c = ln(1 + sqrt(2)) / 2.
BETA_CRITICAL = np.log(1 + np.sqrt(2)) / 2


@dataclass(frozen=True)
class Observable:
    """An extensive, integer-valued observable sampled from the lattice.

    Both quantities we track (the total energy and the total magnetization) are
    sums of products of +/-1 spins, so they are always integers.
    """

    name: str
    dtype: type[np.signedinteger[Any]]
    sample_fun: Callable[[SpinLattice], int]


class SpinLattice:
    """An n x n lattice of +/-1 spins with periodic boundary conditions."""

    def __init__(self, n: int) -> None:
        if n % 2 != 0:
            raise ValueError(
                f"lattice size must be even so that the checkerboard coloring "
                f"survives the periodic wrap-around, got {n}"
            )
        self.n = n
        self.arr = np.zeros((n, n), dtype=np.int8)

        # Checkerboard coloring. Every nearest neighbor of a "black" site is
        # "white" and vice versa, so all the sites of one color can be updated
        # simultaneously without any of them seeing a stale neighbor.
        i, j = np.indices((n, n))
        black = (i + j) % 2 == 0
        self.colors = (black, ~black)

    def randomize(self, rng: Generator) -> None:
        """Reset to a uniformly random configuration -- the beta = 0 state."""
        self.arr[:] = rng.choice((-1, 1), size=(self.n, self.n))

    def __getitem__(self, key: tuple[int, int]) -> np.int8:
        return self.arr[key]

    def __repr__(self) -> str:
        return repr(self.arr)

    def sum(self) -> int:
        return int(self.arr.sum())

    def neighbor_sums(self) -> NDArray[np.int8]:
        """Sum of the four periodic nearest neighbors, for every site at once."""
        arr = self.arr
        return (
            np.roll(arr, 1, axis=0) + np.roll(arr, -1, axis=0)
            + np.roll(arr, 1, axis=1) + np.roll(arr, -1, axis=1)
        )

    def sample_observable(self, obs: Observable) -> int:
        return obs.sample_fun(self)


class MetropolisMC:
    """Metropolis sampler for one lattice, reusable across inverse temperatures."""

    def __init__(
        self,
        lattice_size: int,
        gen: Generator,
        obs: dict[str, Observable],
        burn_in_sweeps: int = BURN_IN_SWEEPS,
        measure_sweeps: int = MEASURE_SWEEPS,
    ) -> None:
        self.n = lattice_size
        self.lattice = SpinLattice(lattice_size)
        self.obs = obs
        self.rng = gen
        self.burn_in_sweeps = burn_in_sweeps
        self.measure_sweeps = measure_sweeps

        # One sample per measurement sweep: a sweep is the natural unit of
        # Monte Carlo time, and sampling any faster just piles up correlated
        # values that do not sharpen the average.
        self.observations = {
            obs_name: np.zeros((measure_sweeps,), dtype=observable.dtype)
            for obs_name, observable in self.obs.items()
        }

    def run(self, beta: float, verbose: bool = True) -> dict[str, float]:
        """Equilibrate at `beta`, then average the observables.

        Picks up from whatever configuration the lattice is currently in, so a
        caller walking through nearby betas can hand each run the previous
        one's equilibrium state. Call `lattice.randomize()` first for an
        independent start.
        """
        if verbose:
            print(f"Running simulation for beta={beta}, lattice_size={self.n}")

        for _ in range(self.burn_in_sweeps):
            self._sweep(beta)

        for step in range(self.measure_sweeps):
            self._sweep(beta)
            for obs_key, observable in self.obs.items():
                self.observations[obs_key][step] = self.lattice.sample_observable(observable)

        results: dict[str, float] = {"beta": beta}
        for obs_key in self.obs:
            mean = float(self.observations[obs_key].mean())
            results[f"{obs_key}_mean"] = mean
            if verbose:
                print(f"{obs_key}_mean={mean}")
        return results

    def _sweep(self, beta: float) -> None:
        """One full sweep: both checkerboard colors, in sequence."""
        for color in self.lattice.colors:
            self._update_color(beta, color)

    def _update_color(self, beta: float, color: NDArray[np.bool_]) -> None:
        arr = self.lattice.arr

        # Flipping s_i flips the sign of its four bonds, so dE = 2 s_i * (sum of
        # neighbors). Recomputed per color, because the previous half-sweep
        # moved the other color's spins.
        delta_e = 2 * arr * self.lattice.neighbor_sums()

        # Metropolis: accept with probability min(1, exp(-beta dE)). Clamping the
        # exponent at 0 expresses the min() directly and keeps exp() from
        # overflowing when -beta*dE is large and positive.
        accept_prob = np.exp(np.minimum(-beta * delta_e, 0.0))
        flip = color & (self.rng.random(arr.shape) < accept_prob)
        np.negative(arr, out=arr, where=flip)

    def print_lattice(self) -> None:
        print(self.lattice)


def total_energy(lattice: SpinLattice) -> int:
    # Only the +row and +col neighbor directions -- summing all four would
    # count every bond twice, once from each of its two endpoint sites.
    arr = lattice.arr.astype(np.int32)
    right = np.roll(arr, -1, axis=1)
    down = np.roll(arr, -1, axis=0)
    return int(-(arr * right + arr * down).sum())


def abs_magnetization(lattice: SpinLattice) -> int:
    # The model has no external field, so +M and -M are exactly as likely and
    # <M> averages to zero by symmetry however ordered the lattice is. The
    # magnitude is the order parameter that actually distinguishes the phases.
    return abs(lattice.sum())


@dataclass(frozen=True)
class SweepResult:
    """Equilibrium averages over the whole beta sweep, in ascending beta order."""

    betas: NDArray[np.floating[Any]]
    energies: NDArray[np.floating[Any]]
    abs_magnetizations: NDArray[np.floating[Any]]


@cache
def run_beta_sweep() -> SweepResult:
    """Run the sampler once per beta. Cached: both figures share one sweep.

    The sweep starts at beta = 0 and walks outwards in both directions, handing
    each run the previous one's equilibrium configuration. Two reasons: a
    uniformly random lattice *is* the beta = 0 equilibrium state, so the walk
    starts from an exactly-known point; and because consecutive betas differ so
    little, each run begins somewhere very close to its own equilibrium. Starting
    every beta from scratch instead lets the lattice freeze into a striped
    two-domain state just past the critical point, which single-spin-flip
    dynamics is far too slow to escape -- that traps the energy well above its
    equilibrium value and puts a visible kink in the entropy curve.
    """
    rng = np.random.default_rng(SEED)
    mc = MetropolisMC(
        lattice_size=LATTICE_SIZE,
        gen=rng,
        obs={
            "Energy": Observable("Energy", dtype=np.int32, sample_fun=total_energy),
            "Magnetization": Observable("Magnetization", dtype=np.int32, sample_fun=abs_magnetization),
        },
    )

    betas = np.sort(BETAS)
    anchor = int(np.flatnonzero(np.isclose(betas, 0.0, atol=1e-12))[0])
    results: dict[int, dict[str, float]] = {}

    # Positive-beta half, cooling from the random beta = 0 state.
    mc.lattice.randomize(rng)
    for idx in range(anchor, len(betas)):
        results[idx] = mc.run(beta=float(betas[idx]), verbose=False)

    # Negative-beta half, starting over from beta = 0 and heating past infinity.
    mc.lattice.randomize(rng)
    for idx in range(anchor - 1, -1, -1):
        results[idx] = mc.run(beta=float(betas[idx]), verbose=False)

    ordered = [results[idx] for idx in range(len(betas))]
    return SweepResult(
        betas=betas,
        energies=np.array([result["Energy_mean"] for result in ordered]),
        abs_magnetizations=np.array([result["Magnetization_mean"] for result in ordered]),
    )


def entropy(
    betas: NDArray[np.floating[Any]],
    energies: NDArray[np.floating[Any]],
    lattice_size: int,
) -> tuple[NDArray[np.floating[Any]], int]:
    """Estimate S(beta) via thermodynamic integration, anchored at the
    beta=0 reference point where every microstate is equally likely:

        S(beta) = N*ln(2) + beta*E(beta) - integral_0^beta E(beta') dbeta'

    `betas` and `energies` must already be sorted by ascending beta. Returns the
    entropies in that same order, plus the index of the beta=0 anchor.
    """
    zero_indices = np.flatnonzero(np.isclose(betas, 0.0, atol=1e-12))
    if zero_indices.size == 0:
        raise ValueError("beta=0 must be in the sweep to anchor the entropy reference point")
    k0 = int(zero_indices[0])

    n_spins = lattice_size**2
    s0 = n_spins * np.log(2)

    # Cumulative integral of E(beta') over the *whole* sorted sweep, then
    # re-zeroed at the beta=0 index -- this handles the negative-beta half
    # of the sweep automatically (no separate branch needed): for k < k0 the
    # subtraction comes out negative.
    cumulative = cumulative_trapezoid(energies, betas, initial=0)
    integral_from_zero = cumulative - cumulative[k0]

    return s0 + betas * energies - integral_from_zero, k0


def plot_entropy_vs_energy(ax: Axes) -> Axes:
    """Entropy against energy, with the two temperature branches picked out."""
    sweep = run_beta_sweep()
    entropies, k0 = entropy(sweep.betas, sweep.energies, LATTICE_SIZE)

    # Sorted by ascending beta, so everything before the beta=0 anchor is the
    # negative-temperature (high-energy) branch and everything after it is the
    # ordinary positive-temperature one.
    ax.plot(
        sweep.energies[:k0], entropies[:k0],
        marker="o", ms=1, lw=1, color="#880808",
        label=r"$\beta < 0$: negative temperature",
    )
    ax.plot(
        sweep.energies[k0:], entropies[k0:],
        marker="o", ms=1, lw=1, color="#6495ED",
        label=r"$\beta > 0$: positive temperature",
    )
    ax.axvline(0.0, color="0.6", lw=0.8)
    ax.set_xlabel(r"Energy $E$ [$J$]")
    ax.set_ylabel(r"Entropy $S$ [$k_B$]")
    ax.set_title(f"Entropy peaks at $E = 0$ ({LATTICE_SIZE}x{LATTICE_SIZE}, periodic BCs)")
    ax.legend()
    return ax


def plot_magnetization_vs_beta(ax: Axes) -> Axes:
    """The order parameter, with Onsager's critical point marked."""
    sweep = run_beta_sweep()
    n_spins = LATTICE_SIZE**2

    ax.plot(sweep.betas, sweep.abs_magnetizations / n_spins, lw=1.2, color="#6495ED")
    ax.axvline(
        BETA_CRITICAL, color="#880808", ls="--", lw=1,
        label=rf"$\beta_c = \ln(1 + \sqrt{{2}})\,/\,2 \approx {BETA_CRITICAL:.4f}$",
    )
    ax.set_xlabel(r"Inverse temperature $\beta$ [$1/J$]")
    ax.set_ylabel(r"$\langle |M| \rangle / N$")
    ax.set_title("Spontaneous magnetization switches on below the critical point")
    ax.legend()
    return ax


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    fig, (ax_s, ax_m) = plt.subplots(2, 1, figsize=(8, 8.4), constrained_layout=True)
    plot_entropy_vs_energy(ax_s)
    plot_magnetization_vs_beta(ax_m)
    plt.show()
