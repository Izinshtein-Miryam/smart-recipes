# מתכונים חכם

אתר מתכונים בעברית (RTL) עם ניווט חכם, יצירה חכמה והמלצות, מבוסס Claude API.
פרויקט לימוד והדגמה שרץ מקומית.

- אפיון: [`docs/SPEC.md`](docs/SPEC.md)
- אב-טיפוס מסכים: [`docs/recipe-screens.html`](docs/recipe-screens.html)

## מבנה הריפו

```
backend/            FastAPI + SQLAlchemy 2 + Alembic (Python 3.12)
  app/
    api/routes/     נתיבי API (נתיבים שטרם מומשו נמצאים ב-placeholders.py ומחזירים 501)
    core/           אבטחה (bcrypt, JWT ב-cookie) ו-dependencies של הרשאות
    domain/         לוגיקה טהורה: בדיקת בשר/חלב, חישוב מנות
    models/         טבלאות מסד הנתונים לפי האפיון
    schemas/        סכמות Pydantic לבקשות ותגובות
    services/       שכבות AI: ai (Claude), images (ImageProvider), embeddings
    seed/           נתוני דמה ופקודת seed
    cli.py          create-sysadmin, seed
  alembic/          מיגרציות
  tests/            pytest (כיסוי מינימלי 70%)
frontend/           React + TypeScript + Vite + Tailwind v4 + TanStack Query + React Router
  src/
    api/            fetch wrapper, טיפוסים ו-hooks
    components/     רכיבים משותפים (Layout, RecipeCard...)
    pages/          מסכים (מסכים שטרם מומשו ב-placeholders.tsx)
    routes/         הגדרת הנתיבים
docs/               אפיון ואב-טיפוס
```

## דרישות מוקדמות

- Python 3.12 ו-[uv](https://docs.astral.sh/uv/) (או pip)
- Node.js 22

## התקנה

Backend:

```bash
cd backend
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
.venv/bin/python -m app.cli create-sysadmin --email admin@example.com
```

ב-Windows מחליפים את `.venv/bin/` ב-`.venv\Scripts\`.

ספקי AI אמיתיים (אופציונלי): ממלאים מפתחות ב-`backend/.env`, משנים את `LLM_PROVIDER` / `IMAGE_PROVIDER` / `EMBEDDING_PROVIDER`, ומתקינים את התוספות הנדרשות:

```bash
uv pip install --python .venv/bin/python -e ".[images,embeddings]"
```

כברירת מחדל כל הספקים במצב `mock`, כך שאפשר לפתח ולהריץ בדיקות בלי מפתחות.

Frontend:

```bash
cd frontend
npm install
```

## הרצה

```bash
./dev.sh
```

ב-Windows: `./dev.ps1`. הסקריפט מריץ את השרת על פורט 8000 ואת הממשק על פורט 5173 (Vite מעביר את `/api` ו-`/media` לשרת).

- אתר: http://localhost:5173
- תיעוד API: http://localhost:8000/docs

## בדיקות ואיכות קוד

```bash
cd backend && .venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/mypy app tests
```

```bash
cd frontend && npm test && npm run lint && npm run typecheck
```

Pre-commit (מהשורש, אחרי התקנת ה-backend):

```bash
backend/.venv/bin/pre-commit install
```

GitHub Actions מריץ lint, בדיקות טיפוסים, מיגרציות ובדיקות בכל push (`.github/workflows/ci.yml`).

## מיגרציות

אחרי שינוי במודלים:

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "describe change"
.venv/bin/alembic upgrade head
```

## API

התיעוד המלא, כולל דוגמאות, נמצא ב-`/docs`. סיכום הנתיבים:

| נתיב | תיאור | הרשאה |
| --- | --- | --- |
| `GET /api/recipes` | קטלוג עם מסננים (`kosher_type`, `dish_type`, `difficulty`, `max_minutes`, `q`, `include`, `exclude`, `diet`) ועימוד | כולם |
| `GET /api/recipes/{slug}?servings=` | מתכון מלא עם חישוב כמויות. טיוטות גלויות רק לבעלים ולמנהלי תוכן | כולם |
| `GET /api/recipes/{id}/similar` | 4 מתכונים דומים מאותו סוג (`any_type=true` לביטול) | כולם |
| `GET /api/recommendations/home` | מובחר ועוד 4 לפי הקשר זמן | כולם |
| `GET /api/search/suggest?q=` | השלמה אוטומטית מקומית (עד 8) | כולם |
| `POST /api/search/smart` | משפט חופשי ← מסננים, תוצאות והצעות ריכוך. בלי AI עובר לחיפוש טקסט | כולם |
| `POST /api/assistant/chat` | צ'אט עוזר (SSE): `delta`, `recipes`, `done` / `error` | כולם |
| `POST /api/generate` | יצירה חכמה (SSE): `attempt`, `delta`, `retry`, `done` / `error` | כולם, עם מכסה |
| `POST /api/generate/{id}/save` | שמירת מתכון שנוצר כטיוטה אישית | רשום |
| `GET /api/ingredients?q=` | חיפוש בטבלת הרכיבים | כולם |
| `/api/auth/*`, `PATCH /api/me`, `GET /api/me/recipes` | חשבון, פרופיל ומגבלות תזונה, המתכונים שלי | — / רשום |
| `/api/favorites`, `/api/shopping-list` | מועדפים ורשימת קניות מאוחדת | רשום |
| `/api/admin/recipes`, `/api/admin/ingredients` | ניהול מתכונים ורכיבים | מנהל תוכן |
| `/api/admin/recipes/{id}/images`, `/api/admin/images/{id}/approve` | העלאה, שיפור או יצירה של תמונה, ואישור | מנהל תוכן |
| `/api/system/users`, `/settings`, `/stats`, `/audit` | ניהול מערכת | מנהל מערכת |

נתיבי ה-AI מוגבלים ל-10 קריאות בדקה למשתמש או IP (ניתן לשינוי בהגדרות). כל קריאה ל-Claude נרשמת בטבלת `ai_calls`.

## מצב נוכחי

ה-Backend ממומש לפי האפיון. הבא בתור: מסכי הממשק (`frontend/src/pages/placeholders.tsx`) והרחבת קובץ ה-seed ל-~50 מתכונים.
