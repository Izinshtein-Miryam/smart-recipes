"""Unit normalization so quantities of the same ingredient can be summed."""

# alias -> (canonical unit, factor to canonical)
_UNITS: dict[str, tuple[str, float]] = {
    "גרם": ("גרם", 1),
    "גר": ("גרם", 1),
    "גר'": ("גרם", 1),
    "ג": ("גרם", 1),
    "g": ("גרם", 1),
    'ק"ג': ("גרם", 1000),
    "קג": ("גרם", 1000),
    "קילו": ("גרם", 1000),
    "kg": ("גרם", 1000),
    'מ"ל': ('מ"ל', 1),
    "מל": ('מ"ל', 1),
    "ml": ('מ"ל', 1),
    "ליטר": ('מ"ל', 1000),
    "l": ('מ"ל', 1000),
    "כף": ("כף", 1),
    "כפות": ("כף", 1),
    "כפית": ("כפית", 1),
    "כפיות": ("כפית", 1),
    "כוס": ("כוס", 1),
    "כוסות": ("כוס", 1),
    "יחידה": ("יחידות", 1),
    "יחידות": ("יחידות", 1),
    "יח'": ("יחידות", 1),
}


def normalize_unit(unit: str | None) -> tuple[str | None, float]:
    """Return (canonical unit, factor). Unknown units are returned as-is with factor 1."""
    if unit is None:
        return None, 1.0
    key = unit.strip().lower()
    if key in _UNITS:
        canonical, factor = _UNITS[key]
        return canonical, float(factor)
    return unit.strip(), 1.0


def normalize_quantity(quantity: float | None, unit: str | None) -> tuple[float | None, str | None]:
    canonical, factor = normalize_unit(unit)
    if quantity is None:
        return None, canonical
    return round(quantity * factor, 2), canonical
