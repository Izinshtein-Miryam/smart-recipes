"""Shared enumerations for the data model."""

from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    CONTENT_MANAGER = "content_manager"
    SYSADMIN = "sysadmin"


class KosherType(StrEnum):
    MEAT = "meat"
    DAIRY = "dairy"
    PARVE = "parve"


class DishType(StrEnum):
    STARTER = "starter"
    MAIN = "main"
    SIDE = "side"
    DESSERT = "dessert"
    BAKED = "baked"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RecipeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"


class RecipeSource(StrEnum):
    ADMIN = "admin"
    AI = "ai"


class DietTag(StrEnum):
    GLUTEN_FREE = "gluten_free"
    VEGAN = "vegan"
    SUGAR_FREE = "sugar_free"
    NUT_FREE = "nut_free"


class TimeTag(StrEnum):
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"
    MAKE_AHEAD = "make_ahead"


class ImageOrigin(StrEnum):
    UPLOAD = "upload"
    AI_EDIT = "ai_edit"
    AI_GENERATE = "ai_generate"


class AIFeature(StrEnum):
    SEARCH = "search"
    CHAT = "chat"
    GENERATE = "generate"
    IMAGE = "image"
