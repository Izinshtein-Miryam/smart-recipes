import pytest

from app.domain.kosher import MeatDairyMixError, derive_recipe_kosher_type
from app.domain.servings import scale_quantity
from app.models import KosherType


@pytest.mark.parametrize(
    ("types", "expected"),
    [
        ([], KosherType.PARVE),
        ([KosherType.PARVE], KosherType.PARVE),
        ([KosherType.PARVE, KosherType.MEAT], KosherType.MEAT),
        ([KosherType.DAIRY, KosherType.PARVE], KosherType.DAIRY),
    ],
)
def test_derive_kosher_type(types: list[KosherType], expected: KosherType) -> None:
    assert derive_recipe_kosher_type(types) == expected


def test_meat_dairy_mix_rejected() -> None:
    with pytest.raises(MeatDairyMixError):
        derive_recipe_kosher_type([KosherType.MEAT, KosherType.DAIRY])


def test_scale_quantity() -> None:
    assert scale_quantity(3, 4, 2) == 1.5
    assert scale_quantity(None, 4, 2) is None
    with pytest.raises(ValueError, match="positive"):
        scale_quantity(1, 0, 2)
