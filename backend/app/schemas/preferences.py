from enum import StrEnum

from pydantic import BaseModel


class ThemeMode(StrEnum):
    light = "light"
    dark = "dark"


class ThemeAccent(StrEnum):
    teal = "teal"
    blue = "blue"
    rose = "rose"


class ThemeDensity(StrEnum):
    comfortable = "comfortable"
    compact = "compact"


class ThemePreferences(BaseModel):
    mode: ThemeMode = ThemeMode.light
    accent: ThemeAccent = ThemeAccent.teal
    density: ThemeDensity = ThemeDensity.comfortable
