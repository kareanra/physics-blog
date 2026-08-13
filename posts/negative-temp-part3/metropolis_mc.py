from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.random import Generator
from scipy.integrate import cumulative_trapezoid


@dataclass(frozen=True)
class Observable[T: np.number]:
    """An observable that can be sampled and derived from the lattice during a run."""
    name: str
    dtype: type[T]
    sample_fun: Callable[[SpinLattice], T]


class SpinLattice:
    """An n x n lattice of +/-1 spins with periodic boundary conditions."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.arr = np.ndarray((n, n), dtype=np.int32)
        self.energy = 0

    def randomize(self, rng: Generator) -> None:
        self.arr[:] = rng.choice((-1, 1), size=(self.n, self.n))
        self.energy = total_energy(self)

    def __getitem__(self, key: tuple[int, int]) -> int:
        return self.arr[key]

    def __repr__(self) -> str:
        return repr(self.arr)

    def sum(self) -> int:
        return int(self.arr.sum())

    def neighbor_sum(self, i: int, j: int) -> int:
        """Sum of the four (periodic) nearest-neighbor spins of (i, j)."""
        n = self.n
        return int(
            self.arr[(i - 1) % n, j] + self.arr[(i + 1) % n, j]
            + self.arr[i, (j - 1) % n] + self.arr[i, (j + 1) % n]
        )

    def flip(self, i: int, j: int, delta_e: int) -> None:
        """Flip the spin at (i, j). delta_e must be the ΔE this flip causes."""
        self.arr[i, j] = -self.arr[i, j]
        self.energy += delta_e

    def sample_observable[T](self, obs: Observable[T]) -> T:
        return obs.sample_fun(self)


class MetropolisMC:

    def __init__(self, lattice_size: int, gen: Generator, sampling_rate: int, obs: dict[str, Observable[Any]]) -> None:
        self.n = lattice_size
        self.lattice = SpinLattice(lattice_size)
        self.sampling_rate = sampling_rate
        self.obs = obs
        self.rng = gen

        # run() samples every `sampling_rate`-th step across n**2 total steps,
        # so this needs ceil(n**2 / sampling_rate) slots -- one per sample.
        obs_arr_len = (lattice_size**2 + sampling_rate - 1) // sampling_rate
        self.observations = {
            obs_name: np.ndarray((obs_arr_len,), dtype=obs.dtype) for obs_name, obs in self.obs.items()
        }
        self.random_arr = self.rng.uniform(low=0.0, high=1.0, size=(lattice_size**2,))

        self.lattice.randomize(self.rng)


    def run(self, beta: float, verbose: bool = True) -> dict[str, float]:
        if verbose:
            print(f"Running simulation for beta={beta}, lattice_size={self.n}")

        for i in range(self.n**2):
            self._run_once(i, beta)

        if verbose:
            print(f"E_f={self.lattice.energy}")

        results: dict[str, float] = {"beta": beta, "E_f": float(self.lattice.energy)}
        for obs_key in self.obs:
            mean = float(self.observations[obs_key].mean())
            results[f"{obs_key}_mean"] = mean
            if verbose:
                print(f"{obs_key}_mean={mean}")
        return results


    def _run_once(self, i: int, beta: float) -> None:
        site_i = int(self.rng.integers(low=0, high=self.n))
        site_j = int(self.rng.integers(low=0, high=self.n))

        delta_e = 2 * int(self.lattice[site_i, site_j]) * self.lattice.neighbor_sum(site_i, site_j)

        if self.random_arr[i] <= min(1.0, np.exp(-beta * delta_e)):
            self.lattice.flip(site_i, site_j, delta_e)

        if i % self.sampling_rate == 0:
            sample_idx = i // self.sampling_rate
            for obs_key in self.obs:
                self.observations[obs_key][sample_idx] = self.lattice.sample_observable(self.obs[obs_key])


    def print_lattice(self) -> None:
        print(self.lattice)


def total_energy(lattice: SpinLattice) -> int:
    # Only the +row and +col neighbor directions -- summing all four would
    # count every bond twice, once from each of its two endpoint sites.
    arr = lattice.arr
    right = np.roll(arr, -1, axis=1)
    down = np.roll(arr, -1, axis=0)
    return int(-(arr * right + arr * down).sum())


def total_magnetization(lattice: SpinLattice) -> int:
    return lattice.sum()


def entropy(betas: list[float], energies: list[float], lattice_size: int) -> tuple[np.ndarray, int]:
    """Estimate S(beta) via thermodynamic integration, anchored at the
    beta=0 reference point where every microstate is equally likely:

        S(beta) = N*ln(2) + beta*E(beta) - integral_0^beta E(beta') dbeta'
    """
    order = np.argsort(betas)
    beta_arr = np.asarray(betas)[order]
    energy_arr = np.asarray(energies)[order]

    zero_indices = np.flatnonzero(beta_arr == 0)
    if zero_indices.size == 0:
        raise ValueError("beta=0 must be in the sweep to anchor the entropy reference point")
    k0 = int(zero_indices[0])

    n_spins = lattice_size**2
    s0 = n_spins * np.log(2)

    # Cumulative integral of E(beta') over the *whole* sorted sweep, then
    # re-zeroed at the beta=0 index -- this handles the negative-beta half
    # of the sweep automatically (no separate branch needed): for k < k0 the
    # subtraction comes out negative.
    cumulative = cumulative_trapezoid(energy_arr, beta_arr, initial=0)
    integral_from_zero = cumulative - cumulative[k0]

    return s0 + beta_arr * energy_arr - integral_from_zero, k0


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    results = []
    for b in np.linspace(-1.0, 1.0, 501):
        mc = MetropolisMC(
            lattice_size=50,
            gen=rng,
            sampling_rate=5,
            obs={
                "Energy": Observable("Energy", dtype=np.int32, sample_fun=total_energy),
                "Magnetization": Observable("Magnetization", dtype=np.int32, sample_fun=total_magnetization),
            },
        )
        results.append(mc.run(beta=b, verbose=False))
    betas = [result["beta"] for result in results]
    energies = [result["Energy_mean"] for result in results]
    entropies, k0 = entropy(betas, energies, lattice_size=50)

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(energies[:k0], entropies[:k0], marker="o", ms=1, color="#880808")  # negative-T half
    ax.plot(energies[k0:], entropies[k0:], marker="o", ms=1, color="#6495ED")  # positive-T half
    ax.set_xlabel("Energy")
    ax.set_ylabel("Entropy S")
    ax.set_title("Entropy vs. energy (2D Ising, periodic BCs)")
    plt.show()
