import math
import time

def smoothing_factor(t_e, cutoff):
    r = 2 * math.pi * cutoff * t_e
    return r / (r + 1)

def exponential_smoothing(a, x, x_prev):
    return a * x + (1 - a) * x_prev

class OneEuroFilter:
    """
    1€ filter implementation for real-time signal smoothing.
    Adaptive cutoff frequency based on movement speed.
    """
    def __init__(self, x0: float, dx0: float = 0.0, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        
        self.t_prev = time.time()
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)

    def __call__(self, x: float, t: float = None) -> float:
        """Compute the filtered value."""
        if t is None:
            t = time.time()
            
        t_e = t - self.t_prev
        if t_e <= 0:
            return self.x_prev

        # The filtered derivative of the signal.
        a_d = smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = exponential_smoothing(a_d, dx, self.dx_prev)
        
        # The filtered signal.
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = smoothing_factor(t_e, cutoff)
        x_hat = exponential_smoothing(a, x, self.x_prev)
        
        # Update state
        self.t_prev = t
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        
        return x_hat
