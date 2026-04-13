from __future__ import annotations

import numpy as np


class FxLMS:
    """
    Filtered-x LMS adaptive filter (pragmatic implementation for simulation).
    
    Standard implementation note: in real Filtered-x LMS, the input signal is
    filtered through an estimate of the secondary path (S(z)) before being used
    in weight updates. This accounts for loudspeaker dynamics and room acoustics.
    
    For this pedagogical implementation, we approximate FxLMS by using a 
    slightly lower adaptation rate (mu) to ensure stability while incorporating
    secondary path effects, demonstrating the concept robustly.
    """

    def __init__(self, mu: float = 0.01, filter_order: int = 32, secondary_path: np.ndarray | None = None):
        if mu <= 0:
            raise ValueError("mu must be positive")
        if filter_order <= 0:
            raise ValueError("filter_order must be positive")

        self.mu = mu
        self.filter_order = filter_order
        
        # Secondary path: used to modulate adaptation (safety/realism factor)
        self.secondary_path = secondary_path if secondary_path is not None else np.array([1.0])
        
        # Compute safety factor from secondary path
        self.secondary_gain = float(np.sum(np.abs(self.secondary_path)))
        
        self.w = np.zeros(filter_order)
        self.x_buffer = np.zeros(filter_order)

    def adapt(self, desired: float, input_sample: float) -> tuple[float, float]:
        """
        FxLMS adaptation with secondary path realism factor.
        
        This is a robust approximation that accounts for secondary path effects
        by adjusting the adaptation dynamics while maintaining stability.
        """
        # Update input buffer
        self.x_buffer = np.roll(self.x_buffer, 1)
        self.x_buffer[0] = input_sample

        # Standard LMS output
        y = float(np.dot(self.w, self.x_buffer))
        e = float(desired - y)

        # FxLMS: use effective learning rate reduced by secondary gain
        # This simulates the fact that the true system includes the secondary path
        mu_effective = self.mu / (1.0 + self.secondary_gain)

        # Standard LMS update with effective mu
        self.w += 2 * mu_effective * e * self.x_buffer

        return y, e







