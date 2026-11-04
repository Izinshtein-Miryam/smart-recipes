from typing import Any

import pytest

from app.domain.servings import scale_ingredients


def test_scale_ingredients() -> None:
    items: list[dict[str, Any]] = [
        {"name": "foo", "quantity": 1.5, "unit": "g", "note": None},
        {"name": "bar", "quantity": None, "unit": None, "note": "Lorem"},
    ]
    scaled = scale_ingredients(items, 2, 6)
    assert scaled[0]["quantity"] == 4.5
    assert scaled[1]["quantity"] is None
    assert items[0]["quantity"] == 1.5  # input is not mutated


def test_scale_rejects_non_positive_servings() -> None:
    with pytest.raises(ValueError):
        scale_ingredients([], 0, 2)
