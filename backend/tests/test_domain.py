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


from datetime import datetime  # noqa: E402

from app.domain.similarity import jaccard  # noqa: E402
from app.domain.time_context import time_context, time_match  # noqa: E402
from app.domain.units import normalize_quantity, normalize_unit  # noqa: E402
from app.models import TimeTag  # noqa: E402


def test_normalize_units() -> None:
    assert normalize_unit("כפות") == ("כף", 1.0)
    assert normalize_unit(None) == (None, 1.0)
    assert normalize_unit(" קורט ") == ("קורט", 1.0)
    assert normalize_quantity(1.5, 'ק"ג') == (1500, "גרם")
    assert normalize_quantity(None, "ליטר") == (None, 'מ"ל')


def test_time_context_and_match() -> None:
    assert time_context(datetime(2026, 11, 2, 7)).tag == TimeTag.MORNING  # Monday
    assert time_context(datetime(2026, 11, 6, 7)).tag == TimeTag.MAKE_AHEAD  # Friday
    assert time_context(datetime(2026, 11, 2, 2)).tag == TimeTag.EVENING
    assert time_match(TimeTag.NOON, ["noon"], 60, "hard", "side") == 1.0
    assert time_match(TimeTag.MORNING, [], 15, "easy", "side") == 0.5
    assert time_match(TimeTag.EVENING, [], 60, "hard", "main") == 0.5
    assert time_match(TimeTag.NOON, [], 15, "easy", "main") == 0.0


def test_jaccard() -> None:
    assert jaccard([1, 2], [2, 3]) == 1 / 3
    assert jaccard([], []) == 0.0
