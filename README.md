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

**מומש (כל ה-MVP לפי `docs/SPEC.md`):**

- Backend: מודל נתונים ומיגרציה, `ai_service` (חיפוש לפי מצרכים, הערכה תזונתית, התאמה, צ'אט עם streaming ולולאת Tools מוגבלת ל-3 סבבים; timeout של 30 שניות, ניסיון חוזר אחד על 429/5xx, תיעוד טוקנים), קטלוג עם סינון ועימוד (`limit`/`offset`, הכותרת `X-Total-Count`), שינוי כמויות לפי `?servings=`, הגשת מתכון עם הגבלה, התחברות מנהל ותור אישורים עם חיפוש.
- Frontend: קטלוג עם מסננים השמורים ב-URL ועימוד, עמוד מתכון (בורר מנות, הדפסה, שיתוף, התאמה מהירה וחופשית), עוזר צ'אט צדדי, מה יש לי במקרר, תצוגת מתכון מותאם עם שמירה, הגשת מתכון, ניהול (התחברות, תור, עריכה, אישור ודחייה) ומצב בישול (שלב אחר שלב, החלקה, טיימר, Wake Lock).
- נתוני דמה: `python -m app.cli seed` טוען 50 מתכונים מאושרים (25 בעברית ו-25 באנגלית; בלי ערבוב בשר וחלב). בדוקר: `docker compose run --rm backend python -m app.cli seed`.

**נדרש מהמפעיל:** `OPENAI_API_KEY` אמיתי ב-`.env`. בלי מפתח, פיצ'רי ה-AI מחזירים 503 `ai_unavailable` והאתר ממשיך לעבוד. מומלץ לבדוק עם מפתח אמיתי שהטקסט הראשון בצ'אט מגיע תוך 2 שניות ושההתאמה מסתיימת בתוך ה-timeout.

**ביצועים:** רשימת הקטלוג מוגשת משאילתה אחת עם אינדקסים על `status`, `kashrut`, `difficulty`, `prep_minutes` ו-`equipment`, ללא AI. יש למדוד מול מסד הפריסה (50 מתכונים) ולוודא מתחת ל-300ms.

**הערה על ה-Issues:** חלק מה-Issues נכתבו לפני המעבר ל-MVP הנוכחי (טבלת רכיבים, משתמשים רשומים, `/generate`), ואינם חלק מהאפיון הקיים; הם לא מומשו.
