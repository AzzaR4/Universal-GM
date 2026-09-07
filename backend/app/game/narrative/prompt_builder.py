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

        # Warn the narrator about dangerous conditions / low resources.
        warnings = []
        for k, v in res.items():
            cur = v.get("current", 0)
            mx = v.get("max", 0) or 0
            if mx and cur / mx <= 0.25 and k.lower() in {"hp", "health", "endurance"}:
                warnings.append(f"{pc.name}'s {k} is critically low ({cur}/{mx})")
        if warnings:
            parts.append("Warnings: " + "; ".join(warnings))

    if npcs:
        parts.append("\nNPCs present (stay consistent with each personality):")
        for n in npcs:
            activity = f" ({n.current_activity})" if n.current_activity else ""
            parts.append(f"- {n.name}: {n.description}{activity}")
            personality = n.personality or {}
            traits = personality.get("traits") or personality.get("personality")
            if traits:
                parts.append(f"    Personality: {traits}")
            for extra_key in ("motivation", "goal", "voice", "mood"):
                if personality.get(extra_key):
                    parts.append(f"    {extra_key.capitalize()}: {personality[extra_key]}")

    # Active quests give the narration direction and stakes.
    active_quests = [q for q in state.quests if q.status == "active"]
    if active_quests:
        parts.append("\n=== ACTIVE QUESTS ===")
        for q in active_quests[:5]:
            parts.append(f"- {q.title}")

    if relevant:
        parts.append("\n=== RELEVANT MEMORIES ===")
        for m in relevant:
            parts.append(f"- {m}")

    if short_term:
        parts.append("\n=== RECENT EVENTS (most recent last) ===")
        for s in short_term[-5:]:
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
        # Surface any ruleset-specific dice detail so the narrator honours it exactly.
        for detail_key in ("feat_die", "success_dice", "sixes", "tn", "successes", "banes",
                           "pushed", "panic", "ill_omen", "auto_success"):
            if detail_key in d:
                parts.append(f"  {detail_key}: {d[detail_key]}")
    parts.append(f"Outcome: {result.outcome_label}")
    parts.append(f"Mechanical summary: {result.mechanical_description}")
    if result.state_mutations:
        parts.append("State changes applied:")
        for m in result.state_mutations:
            parts.append(f"- {m.to_dict()}")

    parts.append("\n=== NARRATION INSTRUCTIONS ===")
    parts.append(
        "Narrate the outcome of this action vividly and consistently with the mechanical result "
        "above. Follow these constraints strictly:"
    )
    parts.append(
        "1. NEVER contradict, recompute, or invent dice results, damage, hit points, or any "
        "numeric mechanic — the values above are authoritative."
    )
    parts.append(
        "2. Do NOT restate raw numbers; weave the mechanical outcome into the fiction so the "
        "consequences are clear from the prose."
    )
    parts.append(
        "3. Stay in the established fiction and voice; keep NPCs true to their personalities and "
        "end at a natural beat that invites the player's next action."
    )

    return system, "\n".join(parts)
