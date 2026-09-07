"""Tests for the dice parser and roller."""
from __future__ import annotations

import random

import pytest

from app.game.rules.dice import DiceError, parse_dice, roll_dice


def test_parse_standard():
    assert parse_dice("2d6+3") == (2, 6, 3)
    assert parse_dice("1d20") == (1, 20, 0)
    assert parse_dice("d6") == (1, 6, 0)
    assert parse_dice("3d8-2") == (3, 8, -2)


def test_parse_whitespace_and_case():
    assert parse_dice(" 2 D 6 + 1 ") == (2, 6, 1)
    assert parse_dice("1D20") == (1, 20, 0)


def test_parse_invalid():
    for bad in ["", "abc", "2x6", "d", "0d6", "2d0", "6"]:
        with pytest.raises(DiceError):
            parse_dice(bad)


def test_roll_ranges():
    rng = random.Random(42)
    for _ in range(200):
        result = roll_dice("2d6+3", rng=rng)
        assert result.num_dice == 2
        assert result.sides == 6
        assert result.modifier == 3
        assert len(result.rolls) == 2
        assert all(1 <= r <= 6 for r in result.rolls)
        assert result.total == sum(result.rolls) + 3
        assert 5 <= result.total <= 15


def test_roll_single_die_implicit_one():
    rng = random.Random(7)
    result = roll_dice("d20", rng=rng)
    assert result.num_dice == 1
    assert 1 <= result.total <= 20


def test_roll_to_dict():
    rng = random.Random(1)
    d = roll_dice("1d6", rng=rng).to_dict()
    assert set(d) == {"notation", "num_dice", "sides", "modifier", "rolls", "total"}
