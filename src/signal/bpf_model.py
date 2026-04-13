def blade_passing_frequency(rpm: float, n_blades: int) -> float:
    if rpm <= 0:
        raise ValueError("rpm must be positive")
    if n_blades <= 0:
        raise ValueError("n_blades must be positive")
    return n_blades * (rpm / 60.0)
