from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ingredient, KosherType
from app.seed import load_seed_data

BASIC_NAMES = {"מלח", "פלפל שחור", "שמן", "שמן זית", "מים", "סוכר"}


def _ingredients() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = load_seed_data()["ingredients"]
    return items


def test_ingredient_table_is_large_enough() -> None:
    assert len(_ingredients()) >= 150


def test_ingredient_fields_are_valid() -> None:
    for item in _ingredients():
        assert item["name"].strip() == item["name"] != ""
        assert item["category"]
        assert item["default_unit"]
        KosherType(item["kosher_type"])
        assert all(isinstance(a, str) and a for a in item.get("aliases", []))


def test_names_and_aliases_are_unique() -> None:
    terms = Counter(
        term for item in _ingredients() for term in [item["name"], *item.get("aliases", [])]
    )
    assert [t for t, n in terms.items() if n > 1] == []


def test_basic_ingredients_are_flagged() -> None:
    by_name = {i["name"]: i for i in _ingredients()}
    for name in BASIC_NAMES:
        assert by_name[name].get("is_basic") is True, name
    # Dried spices are basic ingredients, and only pantry staples and spices are basic.
    for item in _ingredients():
        if item["category"] == "תבלינים":
            assert item.get("is_basic") is True, item["name"]
        if item.get("is_basic"):
            assert item["category"] in {"תבלינים", "מזווה"}, item["name"]
            assert item["kosher_type"] == KosherType.PARVE, item["name"]


def test_kosher_type_matches_category() -> None:
    for item in _ingredients():
        if item["category"] == "בשר":
            assert item["kosher_type"] == KosherType.MEAT, item["name"]
        elif item["category"] == "מוצרי חלב":
            assert item["kosher_type"] == KosherType.DAIRY, item["name"]
        else:
            assert item["kosher_type"] != KosherType.MEAT, item["name"]


def test_recipe_ingredients_exist_in_table() -> None:
    names = {i["name"] for i in _ingredients()}
    for recipe in load_seed_data()["recipes"]:
        for name, _, _ in recipe["ingredients"]:
            assert name in names, (recipe["slug"], name)


def test_seed_loads_all_ingredients(seeded_db: Session) -> None:
    assert seeded_db.scalar(select(func.count()).select_from(Ingredient)) == len(_ingredients())
    salt = seeded_db.scalars(select(Ingredient).where(Ingredient.name == "מלח")).one()
    assert salt.is_basic
    assert "מלח גס" in salt.aliases
