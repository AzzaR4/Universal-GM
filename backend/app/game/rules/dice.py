"""Dice notation parser and roller.

Supports notation like: "2d6", "1d20", "d6" (implicit 1), "2d6+3", "1d20-2",
"3d8 + 1". Whitespace is ignored. The number of dice and modifier are optional.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

_DICE_RE = re.compile(r"^\s*(\d*)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


@dataclass
class DiceRoll:
    notation: str
    num_dice: int
    sides: int
    modifier: int
    rolls: list[int] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> dict:
        return {
            "notation": self.notation,
            "num_dice": self.num_dice,
            "sides": self.sides,
            "modifier": self.modifier,
            "rolls": self.rolls,
            "total": self.total,
        }


class DiceError(ValueError):
    """Raised for invalid dice notation."""


def parse_dice(notation: str) -> tuple[int, int, int]:
    """Parse dice notation into (num_dice, sides, modifier).

    Raises DiceError on invalid input.
    """
    if not notation or not isinstance(notation, str):
        raise DiceError("Empty dice notation")
    match = _DICE_RE.match(notation)
    if not match:
        raise DiceError(f"Invalid dice notation: {notation!r}")
    num_raw, sides_raw, mod_raw = match.groups()
    num_dice = int(num_raw) if num_raw else 1
    sides = int(sides_raw)
    if num_dice < 1:
        raise DiceError("Number of dice must be >= 1")
    if sides < 1:
        raise DiceError("Dice must have >= 1 side")
    modifier = 0
    if mod_raw:
        modifier = int(mod_raw.replace(" ", ""))
    return num_dice, sides, modifier


def roll_dice(notation: str, rng: random.Random | None = None) -> DiceRoll:
    """Roll dice per the given notation and return a DiceRoll result."""
    num_dice, sides, modifier = parse_dice(notation)
    r = rng or random
    rolls = [r.randint(1, sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier
    return DiceRoll(
        notation=notation.strip(),
        num_dice=num_dice,
        sides=sides,
        modifier=modifier,
        rolls=rolls,
        total=total,
    )
