from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Kashrut, Recipe, RecipeStatus
from app.seed import BASICS, DAIRY, MEAT, seed


def test_seed_loads_50_published_recipes_idempotently(db: Session) -> None:
    assert seed(db) == 50
    assert seed(db) == 0
    recipes = list(db.scalars(select(Recipe)))
    assert len(recipes) == 50
    assert {r.status for r in recipes} == {RecipeStatus.APPROVED}
    assert {r.kashrut for r in recipes} == set(Kashrut)
    assert {r.lang.value for r in recipes} == {"he", "en"}


def test_seed_never_mixes_meat_and_dairy(db: Session) -> None:
    seed(db)
    meat = {n for m in MEAT for n in m[:2]}
    dairy = {n for d in DAIRY for n in d[:2]}
    for r in db.scalars(select(Recipe)):
        names = {i["name"] for i in r.ingredients}
        assert not (names & meat and names & dairy), r.title
        if r.kashrut == Kashrut.PARVE:
            assert not names & (meat | dairy)
        assert all(b[0] in names or b[1] in names for b in BASICS[:2])


def test_delete_removes_webp_and_original() -> None:
    from app.config import get_settings
    from app.services import storage

    from .test_recipes import PNG

    rel = storage.save_pending(PNG)
    root = get_settings().storage_dir
    assert (root / rel).exists()
    storage.delete(rel)
    assert not (root / rel).exists()
    assert not list((root / "originals").glob("*"))
