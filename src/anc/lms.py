from __future__ import annotations

import numpy as np


class LMS:
    def __init__(self, mu: float = 0.01, filter_order: int = 32):
        if mu <= 0:
            raise ValueError("mu must be positive")
        if filter_order <= 0:
            raise ValueError("filter_order must be positive")

        self.mu = mu
        self.filter_order = filter_order
        self.w = np.zeros(filter_order)
        self.x = np.zeros(filter_order)

    def adapt(self, desired: float, input_sample: float) -> tuple[float, float]:
        self.x = np.roll(self.x, 1)
        self.x[0] = input_sample

        y = float(np.dot(self.w, self.x))
        e = float(desired - y)
        self.w += 2 * self.mu * e * self.x

        return y, e
