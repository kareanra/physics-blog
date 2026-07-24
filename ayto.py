from __future__ import annotations

from math import comb, factorial, floor

EULERS_CONSTANT = 2.718281828459045

def probability(n_correct: int, n: int = 10) -> float:
    n_choose_n_correct = comb(n, n_correct)
    n_factorial = factorial(n)
    derangements = floor((factorial(n - n_correct) / EULERS_CONSTANT) + 1/2)
    return (n_choose_n_correct * derangements) / n_factorial

def plot_probabilities(ax, n: int = 10):
    xs = [k for k in range(n + 1) if k not in (n - 1, n)]
    ys = [probability(k, n) for k in xs]
    ax.plot(xs, ys, color="#5F5E5A")
    return ax
