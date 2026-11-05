"""Demo catalog: 50 approved placeholder recipes (25 designs x Hebrew/English).

Kashrut is derived from the ingredient pools below, so meat and dairy never mix by construction.
Run with `python -m app.cli seed` (idempotent).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Difficulty, Equipment, Kashrut, Lang, Recipe, RecipeStatus

# (he, en, default unit he, default unit en)
MEAT = [
    ("עוף", "chicken", "גרם", "g"),
    ("בקר", "beef", "גרם", "g"),
    ("הודו", "turkey", "גרם", "g"),
]
DAIRY = [
    ("גבינה", "cheese", "גרם", "g"),
    ("יוגורט", "yogurt", "גרם", "g"),
    ("חמאה", "butter", "גרם", "g"),
]
PARVE = [
    ("אורז", "rice", "גרם", "g"),
    ("תפוחי אדמה", "potatoes", "גרם", "g"),
    ("עדשים", "lentils", "גרם", "g"),
    ("גזר", "carrots", "גרם", "g"),
    ("ביצים", "eggs", "יח'", "pcs"),
    ("עגבניות", "tomatoes", "יח'", "pcs"),
    ("פסטה", "pasta", "גרם", "g"),
    ("חומוס", "chickpeas", "גרם", "g"),
]
BASICS = [
    ("מלח", "salt", "צרור", "pinch"),
    ("שמן", "oil", "כף", "tbsp"),
    ("מים", "water", "כוס", "cup"),
]

# (method he, method en, equipment, minutes, difficulty)
METHODS: list[tuple[str, str, Equipment, int, Difficulty]] = [
    ("בתנור", "baked", Equipment.OVEN, 60, Difficulty.EASY),
    ("במחבת", "pan-fried", Equipment.STOVETOP, 25, Difficulty.EASY),
    ("בסיר אחד", "one-pot", Equipment.ONE_POT, 45, Difficulty.MEDIUM),
    ("קר", "cold", Equipment.NO_COOK, 10, Difficulty.EASY),
    ("מאודה", "steamed", Equipment.STOVETOP, 35, Difficulty.MEDIUM),
]


def _build(index: int) -> list[dict[str, Any]]:
    """Two recipes (he, en) for design number `index` (0..24)."""
    kind = [Kashrut.MEAT, Kashrut.DAIRY, Kashrut.PARVE][index % 3]
    pool = {Kashrut.MEAT: MEAT, Kashrut.DAIRY: DAIRY, Kashrut.PARVE: PARVE}[kind]
    main = pool[(index // 3) % len(pool)]
    side = PARVE[(index + 2) % len(PARVE)]
    method = METHODS[index % len(METHODS)]
    difficulty = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD][(index // 2) % 3]
    minutes = method[3] + 5 * (index % 4)
    servings = 2 + index % 5
    out = []
    for lang, i in ((Lang.HE, 0), (Lang.EN, 1)):
        name, side_name, method_name = main[i], side[i], str(method[i])
        unit = main[2 + i]
        title = (
            f"{name} {method_name} עם {side_name} – מתכון דמה {index + 1}"
            if lang == Lang.HE
            else f"{method_name.capitalize()} {name} with {side_name} – demo recipe {index + 1}"
        )
        steps = (
            ["מכינים את המרכיבים", f"מבשלים {method_name} במשך זמן קצוב", "מגישים"]
            if lang == Lang.HE
            else ["Prepare the ingredients", f"Cook ({method_name}) for the set time", "Serve"]
        )
        ingredients = [
            {"name": name, "quantity": 100.0 * (1 + index % 4), "unit": unit, "note": None},
            {"name": side_name, "quantity": 2.0 + index % 3, "unit": side[2 + i], "note": None},
        ] + [{"name": b[i], "quantity": 1.0, "unit": b[2 + i], "note": None} for b in BASICS[:2]]
        out.append(
            {
                "lang": lang,
                "title": title,
                "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "servings": servings,
                "prep_minutes": minutes,
                "difficulty": difficulty,
                "equipment": [method[2]],
                "kashrut": kind,
                "ingredients": ingredients,
                "steps": steps,
                "nutrition": {
                    "calories": 300 + 20 * (index % 7),
                    "protein_g": 10 + index % 20,
                    "carbs_g": 30 + index % 25,
                    "fat_g": 8 + index % 12,
                    "confidence": "low",
                },
            }
        )
    return out


def demo_recipes() -> list[dict[str, Any]]:
    return [r for i in range(25) for r in _build(i)]


def seed(db: Session) -> int:
    """Insert the demo recipes that are not there yet; returns how many were added."""
    existing = set(db.scalars(select(Recipe.title).where(Recipe.submitter_ip_hash == "seed")))
    added = 0
    for values in demo_recipes():
        if values["title"] in existing:
            continue
        db.add(
            Recipe(
                **values,
                status=RecipeStatus.APPROVED,
                submitter_ip_hash="seed",
                approved_at=datetime.now(UTC),
            )
        )
        added += 1
    db.commit()
    return added
