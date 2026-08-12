import numpy as np
from numpy.random import Generator

E_DELTAS = [-8, -4, 0, 4, 8]  # periodic boundaries: every site always has 4 neighbors
NEIGHBORS = [(-1, 0), (0, -1), (1, 0), (0, 1)]


class MetropolisMC:

    def __init__(self, lattice_size: int, rng: Generator, sampling_rate: int):
        self.n = lattice_size
        self.sampling_rate = sampling_rate
        self.rng = rng
        self.random_arr = self.rng.uniform(low=0.0, high=1.0, size=(lattice_size**2,))
        self.lattice = np.ndarray((lattice_size, lattice_size), dtype=np.int32)  # bool?

        spins = self.rng.choice([-1, 1], size=(lattice_size,lattice_size))
        for i in range(lattice_size):
            for j in range(lattice_size):
                self.lattice[i][j] = spins[i][j]

        self.energy = self._total_energy()
        # self.print_lattice()
        print(f"E_i={self.energy}")


    def run(self, beta: float) -> None:
        print(f"Running simulation for beta={beta}, lattice_size={self.n}")
        i = 0
        acc = self._precompute_acc(beta)
        while i < self.n**2:
            self._run_once(i, acc)
            i += 1

        print(f"E_f={self._total_energy()}")


    def _run_once(self, i: int, acc: dict[int, float]) -> None:
        site_i = self.rng.integers(low=0, high=self.n)
        site_j = self.rng.integers(low=0, high=self.n)
        site = self.lattice[site_i][site_j]

        delta_e = 0
        for di, dj in NEIGHBORS:
            neighbor = self.lattice[(site_i + di) % self.n][(site_j + dj) % self.n]
            delta_e += 2 * site * neighbor  # site & neighbor?

        should_flip = self.random_arr[i] <= acc[delta_e]
        # print(f"Should flip? {should_flip} (dE={delta_e}, i, j=({site_i}, {site_j}))")
        if should_flip:
            self.lattice[site_i][site_j] = -site
            self.energy += delta_e


    @staticmethod
    def _precompute_acc(beta: float) -> dict[int, float]:
        return {delta: min(1, np.exp(-beta * delta)) for delta in E_DELTAS}


    def _total_energy(self) -> int:
        # Only the +i and +j directions -- summing all four
        # would count every bond twice, once from each
        # of its two endpoint sites. With periodic BCs this still
        # covers every unique bond exactly once.
        energy = 0
        for site_i in range(self.n):
            for site_j in range(self.n):
                for di, dj in ((1, 0), (0, 1)):
                    neighbor = self.lattice[(site_i + di) % self.n][(site_j + dj) % self.n]
                    energy += -self.lattice[site_i, site_j] * neighbor
        return energy


    def _total_magnetization(self) -> int:
        return self.lattice.sum()


    def print_lattice(self) -> None:
        print(self.lattice)


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    for b in np.linspace(-1.0, 1.0, 50):
        # metropolisMC.run(beta=3.0e-1)
        MetropolisMC(lattice_size=50, rng=rng, sampling_rate=5).run(beta=b)
