"""Assembles the layered narration prompt from state, rules result, and memory."""
from __future__ import annotations

from app.game.rules.base_ruleset import ActionResult
from app.game.rules.rules_engine import rules_engine
from app.game.state.game_state import GameState


def build_narration_prompt(
    state: GameState,
    result: ActionResult,
    short_term: list[str],
    relevant: list[str],
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the narrator."""
    system = rules_engine.system_prompt_fragment(state)

    # ---- Assemble the user prompt with structured context ----
    pc = state.get_player_character()
    loc = state.get_location(state.current_location_id)
    npcs = state.npcs_in_location(state.current_location_id)

    parts: list[str] = []
    parts.append("=== CURRENT SCENE ===")
    if loc:
        parts.append(f"Location: {loc.name}")
        if loc.description:
            parts.append(f"Description: {loc.description}")
        if loc.atmosphere:
            parts.append(f"Atmosphere: {loc.atmosphere}")
    else:
        parts.append("Location: (unspecified)")

    if pc:
        res = (pc.ruleset_data or {}).get("resources", {})
        res_str = ", ".join(
            f"{k}: {v.get('current')}/{v.get('max')}" for k, v in res.items()
        ) or "n/a"
        parts.append(f"\nPlayer character: {pc.name} — {pc.description}")
        parts.append(f"Resources: {res_str}")
        if pc.conditions:
            parts.append(f"Conditions: {', '.join(pc.conditions)}")

    if npcs:
        parts.append("\nNPCs present:")
        for n in npcs:
            activity = f" ({n.current_activity})" if n.current_activity else ""
            parts.append(f"- {n.name}: {n.description}{activity}")

    if relevant:
        parts.append("\n=== RELEVANT MEMORIES ===")
        for m in relevant:
            parts.append(f"- {m}")

    if short_term:
        parts.append("\n=== RECENT EVENTS ===")
        for s in short_term[-6:]:
            parts.append(f"- {s}")

    parts.append("\n=== PLAYER ACTION ===")
    parts.append(f'The player said: "{result.intent.raw_text}"')
    parts.append(f"Interpreted intent: {result.intent.action_type} — {result.intent.description}")

    parts.append("\n=== MECHANICAL RESULT (authoritative — narrate consistently) ===")
    if result.check_required and result.dice_rolled:
        d = result.dice_rolled
        parts.append(
            f"Dice rolled: {d.get('notation')} -> rolls {d.get('rolls')} "
            f"(total {d.get('total')})"
        )
    parts.append(f"Outcome: {result.outcome_label}")
    parts.append(f"Mechanical summary: {result.mechanical_description}")
    if result.state_mutations:
        parts.append("State changes applied:")
        for m in result.state_mutations:
            parts.append(f"- {m.to_dict()}")

    parts.append(
        "\nNarrate the outcome of this action vividly and consistently with the mechanical "
        "result above. Do not restate the numbers; weave them into the fiction."
    )

    return system, "\n".join(parts)
