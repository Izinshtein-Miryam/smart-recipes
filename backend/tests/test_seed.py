from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.kosher import derive_recipe_kosher_type
from app.models import Ingredient, KosherType, Recipe, RecipeStatus
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


# ---- recipes ----

GLUTEN = {
    "קמח לבן", "קמח מלא", "קמח תופח", "פסטה", "לחם", "פיתות", "טורטיות", "בורגול", "קוסקוס",
    "פתיתים", "גריסים", "שיבולת שועל", "בצק עלים", "פירורי לחם", "רוטב סויה",
}  # fmt: skip
SUGAR = {
    "סוכר", "סוכר חום", "אבקת סוכר", "סוכר וניל", "דבש", "סילאן", "ריבה", "שוקולד מריר",
    "שוקולד חלב", "תמרים", "צימוקים", "חמוציות מיובשות",
}  # fmt: skip
NUTS = {"אגוזי מלך", "שקדים", "קשיו", "בוטנים", "צנוברים", "פקאנים"}
ANIMAL_CATEGORIES = {"בשר", "דגים", "מוצרי חלב", "ביצים"}


def _recipes() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = load_seed_data()["recipes"]
    return items


def _ing_names(recipe: dict[str, Any]) -> set[str]:
    return {line[0] for line in recipe["ingredients"]}


def _kosher(recipe: dict[str, Any]) -> KosherType:
    by_name = {i["name"]: KosherType(i["kosher_type"]) for i in _ingredients()}
    return derive_recipe_kosher_type(by_name[n] for n in _ing_names(recipe))


def test_fifty_unique_recipes() -> None:
    recipes = _recipes()
    assert len(recipes) == 50
    assert len({r["slug"] for r in recipes}) == 50
    assert len({r["title"] for r in recipes}) == 50


def test_no_meat_dairy_mixing() -> None:
    for recipe in _recipes():
        _kosher(recipe)  # raises MeatDairyMixError on a mix


def test_distribution_is_balanced() -> None:
    recipes = _recipes()
    kosher = Counter(_kosher(r) for r in recipes)
    assert all(kosher[k] >= 15 for k in KosherType), kosher
    assert set(Counter(r["dish_type"] for r in recipes)) == {
        "starter", "main", "side", "dessert", "baked",
    }  # fmt: skip
    assert min(Counter(r["dish_type"] for r in recipes).values()) >= 5
    difficulty = Counter(r["difficulty"] for r in recipes)
    assert set(difficulty) == {"easy", "medium", "hard"}
    assert min(difficulty.values()) >= 8
    times = Counter(t for r in recipes for t in r["time_tags"])
    assert set(times) == {"morning", "noon", "evening", "make_ahead"}
    assert min(times.values()) >= 8
    diets = Counter(t for r in recipes for t in r["diet_tags"])
    assert {"gluten_free", "vegan", "sugar_free", "nut_free"} <= set(diets)
    assert min(diets.values()) >= 5


def test_diet_tags_are_truthful() -> None:
    categories = {i["name"]: i["category"] for i in _ingredients()}
    for recipe in _recipes():
        names, tags = _ing_names(recipe), set(recipe["diet_tags"])
        if "gluten_free" in tags:
            assert not names & GLUTEN, recipe["slug"]
        if "sugar_free" in tags:
            assert not names & SUGAR, recipe["slug"]
        if "nut_free" in tags:
            assert not names & NUTS, recipe["slug"]
        if "vegan" in tags:
            assert not any(categories[n] in ANIMAL_CATEGORIES for n in names), recipe["slug"]
            assert "דבש" not in names, recipe["slug"]


def test_recipe_structure() -> None:
    for recipe in _recipes():
        slug = recipe["slug"]
        assert recipe["prep_minutes"] >= 0 and recipe["cook_minutes"] >= 0, slug
        assert recipe["servings"] > 0, slug
        assert len(recipe["ingredients"]) >= 4, slug
        assert len(recipe["steps"]) >= 2, slug
        assert len(_ing_names(recipe)) == len(recipe["ingredients"]), slug
        for _, quantity, unit in recipe["ingredients"]:
            assert quantity > 0 and unit, slug


def test_steps_have_timers_and_valid_ingredient_links() -> None:
    timed = 0
    for recipe in _recipes():
        names = _ing_names(recipe)
        linked = set()
        for step in recipe["steps"]:
            assert len(step) == 3, recipe["slug"]
            text, timer, refs = step
            assert text and (timer is None or timer > 0), recipe["slug"]
            assert set(refs) <= names, (recipe["slug"], refs)
            timed += timer is not None
            linked |= set(refs)
        assert linked, recipe["slug"]
    assert timed >= 80


def test_seed_loads_all_recipes_published(seeded_db: Session) -> None:
    recipes = seeded_db.scalars(select(Recipe)).all()
    assert len(recipes) == 50
    assert {r.status for r in recipes} == {RecipeStatus.PUBLISHED}
    kosher = Counter(r.kosher_type for r in recipes)
    assert all(kosher[k] >= 15 for k in KosherType)


def test_seeded_steps_reference_recipe_ingredients(seeded_db: Session) -> None:
    for recipe in seeded_db.scalars(select(Recipe)):
        ids = {line.ingredient_id for line in recipe.ingredients}
        for step in recipe.steps:
            assert set(step.ingredient_ids) <= ids, recipe.slug
