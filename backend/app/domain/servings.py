"""Scaling ingredient quantities to a different number of servings."""


def scale_quantity(
    quantity: float | None, base_servings: int, target_servings: int
) -> float | None:
    if quantity is None:
        return None
    if base_servings <= 0 or target_servings <= 0:
        raise ValueError("servings must be positive")
    return round(quantity * target_servings / base_servings, 2)
