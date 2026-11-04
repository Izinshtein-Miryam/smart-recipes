# סיר ומחבת – אתר מתכונים חכם

אתר מתכונים דו-לשוני (עברית RTL / אנגלית LTR), פתוח לכולם ללא הרשמה, עם חיפוש לפי מצרכים, סינון, ערכים תזונתיים משוערים, התאמת מתכון ועוזר בישול – מבוסס OpenAI Responses API.

- אפיון: [`docs/SPEC.md`](docs/SPEC.md)
- עיצוב: [`docs/design/index.html`](docs/design/index.html)
- אפיון ותשתית קודמים (Claude API, משתמשים): [`docs/archive/`](docs/archive/)

## מבנה הריפו

```
backend/              FastAPI + SQLAlchemy 2 + Alembic (Python 3.12)
  app/
    api/routes/       recipes (ציבורי), ai, admin
    core/             סיסמת מנהל + JWT, dependencies
    domain/           לוגיקה טהורה (שינוי כמויות לפי מנות)
    models/           recipes, ai_usage_log
    schemas/          סכמות Pydantic, כולל סכמות הפלט המובנה של ה-AI
    services/         ai_service (הקוד היחיד שפונה ל-OpenAI), prompts, storage (תמונות)
    cli.py            hash-admin-password, purge-rejected
  alembic/            מיגרציות
  tests/              pytest מול PostgreSQL (כיסוי מינימלי 70%)
frontend/             React + TypeScript + Vite + Tailwind v4 + TanStack Query + react-i18next
  src/i18n/           he.json, en.json, החלפת dir לפי שפה
docker-compose.yml    postgres + backend + frontend (nginx)
```

## הרצה עם Docker Compose

```bash
cp .env.example .env   # למלא POSTGRES_PASSWORD, OPENAI_API_KEY, ADMIN_PASSWORD_HASH, JWT_SECRET
docker compose run --rm backend python -m app.cli hash-admin-password   # מפיק ערך ל-ADMIN_PASSWORD_HASH
docker compose up --build
```

האתר זמין ב-http://localhost:8080. המיגרציות רצות אוטומטית בעליית ה-backend. תמונות נשמרות ב-volume בשם `storage`.

## פיתוח מקומי

דרישות: Python 3.12 עם [uv](https://docs.astral.sh/uv/), Node.js 22, Docker (ל-PostgreSQL).

```bash
cp .env.example .env
cd backend
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env   # הסיסמה ב-DATABASE_URL חייבת להיות זהה ל-POSTGRES_PASSWORD בקובץ בשורש
cd ../frontend && npm install
```

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait postgres
cd backend && .venv/bin/alembic upgrade head
```

```bash
./dev.sh
```

ב-Windows: `./dev.ps1`. הסקריפט מפעיל את PostgreSQL, את השרת (פורט 8000) ואת הממשק (פורט 5173; Vite מעביר את `/api` ו-`/media` לשרת).

- אתר: http://localhost:5173
- תיעוד API: http://localhost:8000/docs

בלי `OPENAI_API_KEY` כל נקודות ה-AI מחזירות 503 `ai_unavailable` (והאישור של מתכון ממשיך לעבוד, עם `nutrition = null`).

## בדיקות ואיכות קוד

בדיקות ה-backend רצות מול PostgreSQL (`TEST_DATABASE_URL`, ברירת מחדל: מסד `recipes_test` ב-localhost). הבדיקות מאפסות את הסכמה במסד הזה, לכן אין להפנות אותו למסד עם נתונים.

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

GitHub Actions מריץ lint, בדיקות טיפוסים, מיגרציות (`alembic upgrade head` + `alembic check`) ובדיקות מול PostgreSQL בכל push.

## מיגרציות

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "describe change"
.venv/bin/alembic upgrade head
```

## תחזוקה

מחיקת תמונות של מתכונים שנדחו לפני יותר מ-7 ימים (מתאים ל-cron יומי):

```bash
docker compose run --rm backend python -m app.cli purge-rejected
```

## מצב נוכחי

**מומש:** מודל הנתונים והמיגרציה, `ai_service` (חיפוש לפי מצרכים, הערכה תזונתית, התאמה – עם ניסיון חוזר אחד ותיעוד טוקנים), נתיבי הקטלוג, הגשת מתכון (אימות תמונה, הגבלת 5 ביום לכל IP), התחברות מנהל ותור אישורים, שלד לקוח עם i18n ורשימת מתכונים ודף מתכון, Docker Compose ו-CI.

**הבא בתור:**

- צ'אט עם SSE ולולאת Tools (`POST /api/ai/chat` מחזיר 501; הגדרות הכלים ב-`CHAT_TOOLS`)
- מסכי הלקוח שטרם נבנו (`frontend/src/pages/placeholders.tsx`): חיפוש מקרר, הגשת מתכון, תצוגת מתכון מותאם, ניהול
- פאנל סינון ברשימת המתכונים
