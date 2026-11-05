"""Shared enumerations. Values are stored in PostgreSQL ENUM types."""

from enum import StrEnum


class Lang(StrEnum):
    HE = "he"
    EN = "en"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Equipment(StrEnum):
    OVEN = "oven"
    STOVETOP = "stovetop"
    ONE_POT = "one_pot"
    NO_COOK = "no_cook"


class Kashrut(StrEnum):
    MEAT = "meat"
    DAIRY = "dairy"
    PARVE = "parve"


class RecipeStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AiFeature(StrEnum):
    FRIDGE_SEARCH = "fridge_search"
    NUTRITION = "nutrition"
    ADAPT = "adapt"
    CHAT = "chat"
