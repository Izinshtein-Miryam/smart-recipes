"""System prompts and JSON schemas for the text-AI features."""

from typing import Any

_KOSHER = ["meat", "dairy", "parve"]
_DISH = ["starter", "main", "side", "dessert", "baked"]
_DIFFICULTY = ["easy", "medium", "hard"]
_TIME_TAGS = ["morning", "noon", "evening", "make_ahead"]


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


FILTERS_SCHEMA = _obj(
    {
        "kosher_type": _nullable({"type": "string", "enum": _KOSHER}),
        "dish_type": _nullable({"type": "string", "enum": _DISH}),
        "difficulty": _nullable({"type": "string", "enum": _DIFFICULTY}),
        "max_minutes": _nullable({"type": "integer"}),
        "include_ingredients": {"type": "array", "items": {"type": "string"}},
        "exclude_ingredients": {"type": "array", "items": {"type": "string"}},
        "diet_tags": {"type": "array", "items": {"type": "string"}},
        "text": _nullable({"type": "string"}),
    }
)

DIET_TAGS_HELP = (
    "תגיות תזונה אפשריות: gluten_free (ללא גלוטן), sugar_free (ללא סוכר), "
    "nut_free (ללא אגוזים), vegan (טבעוני), low_fat (דל שומן)."
)

SMART_SEARCH_SYSTEM = f"""אתה מפענח בקשות חיפוש באתר מתכונים בעברית.
המר את המשפט של המשתמש למסננים מובנים לפי הסכמה. אל תמציא מסננים שלא נאמרו.
- kosher_type: meat=בשרי, dairy=חלבי, parve=פרווה.
- dish_type: starter=ראשונה, main=עיקרית, side=תוספת, dessert=קינוח, baked=מאפה.
- max_minutes: זמן הכנה כולל מרבי בדקות ("חצי שעה" = 30).
- include_ingredients / exclude_ingredients: שמות רכיבים בעברית, ביחיד או כפי שנכתבו.
- {DIET_TAGS_HELP}
- text: מילות מפתח שלא נכנסו לשום מסנן אחר (למשל שם מנה), אחרת null.
"""

FILTERS_MARKER = "###FILTERS###"

ASSISTANT_SYSTEM = f"""אתה עוזר מטבח באתר מתכונים בעברית. אתה עוסק במתכונים ובישול בלבד.
אם השאלה אינה קשורה לבישול או למתכונים, סרב בנימוס במשפט אחד והצע לעזור במציאת מתכון.
מטרתך לעזור למשתמש למצוא עד 3 מתכונים מתוך הקטלוג של האתר.
- אם הבקשה עמומה מאוד, שאל שאלת הבהרה אחת בלבד. אם כבר שאלת שאלת הבהרה בשיחה, אל תשאל שוב.
- אל תמציא מתכונים ואל תכתוב מתכונים בעצמך. המתכונים נשלפים מהקטלוג לפי המסננים שתחזיר.
- תשובתך קצרה (עד שני משפטים) ובעברית.

מבנה התשובה: קודם הטקסט למשתמש, ואז שורה חדשה עם {FILTERS_MARKER} ואחריה אובייקט JSON
אחד בשורה אחת עם המפתחות: kosher_type, dish_type, difficulty, max_minutes,
include_ingredients, exclude_ingredients, diet_tags, text (אותה משמעות כמו בחיפוש).
כשאתה שואל שאלת הבהרה או מסרב, כתוב אחרי הסימון null במקום אובייקט.
{DIET_TAGS_HELP}
"""

_INGREDIENT = _obj(
    {
        "name": {"type": "string"},
        "quantity": {"type": "number"},
        "unit": {"type": "string"},
        "kosher_type": {"type": "string", "enum": _KOSHER},
        "note": _nullable({"type": "string"}),
    }
)
_STEP = _obj({"text": {"type": "string"}, "timer_seconds": _nullable({"type": "integer"})})

GENERATED_RECIPE_SCHEMA = _obj(
    {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "servings": {"type": "integer"},
        "prep_minutes": {"type": "integer"},
        "cook_minutes": {"type": "integer"},
        "difficulty": {"type": "string", "enum": _DIFFICULTY},
        "dish_type": {"type": "string", "enum": _DISH},
        "kosher_type": {"type": "string", "enum": _KOSHER},
        "diet_tags": {"type": "array", "items": {"type": "string"}},
        "time_tags": {"type": "array", "items": {"type": "string", "enum": _TIME_TAGS}},
        "ingredients": {"type": "array", "items": _INGREDIENT},
        "steps": {"type": "array", "items": _STEP},
        "changes": {"type": "array", "items": {"type": "string"}},
    }
)

GENERATE_SYSTEM = f"""אתה שף שכותב מתכונים בעברית לאתר מתכונים כשר.
כתוב מתכון אחד מלא לפי הסכמה. כללים מחייבים:
- לעולם אין לערבב רכיבים בשריים וחלביים באותו מתכון.
- kosher_type של המתכון: meat אם יש רכיב בשרי, dairy אם יש רכיב חלבי, אחרת parve.
- לכל רכיב: שם בעברית, כמות מספרית חיובית, יחידה (גרם, מ"ל, כף, כפית, כוס, יחידות...)
  ו-kosher_type של הרכיב עצמו (ביצים, דגים, ירקות ודגנים הם parve).
- שלבים ברורים וממוספרים לפי הסדר. timer_seconds רק לשלב שיש בו המתנה או בישול בזמן מוגדר.
- {DIET_TAGS_HELP}
- changes: רשימה ריקה, אלא אם התבקשת להתאים מתכון קיים. אז פרט כל שינוי במשפט קצר.
"""
