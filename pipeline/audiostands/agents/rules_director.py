"""The rules Director: the same tension plan as the Foundry Director, from file 39's rules. OWNER: A (potencialbg).

It is the fallback for any window where the model call fails or its reply is rejected, and the whole Director when
DIRECTOR=rules (no quota; drop-list item 5). It reads the same firewalled features, so it can't see outcomes either.
For "danger" and "none" it reproduces the Stage 3 build-up exactly, so a rules build is byte-identical to Stage 3.
"""

from __future__ import annotations

from audiostands.agents.director import Plan, regained, set_piece
from audiostands.commentary.templates import BUILD_MIN_XG, LEAD_S

NAME = "rules_v1"
BIG_XG = 0.25  # file 39: a big chance gets the "danger" phrasing


def plan(feat: dict) -> Plan:
    xg = feat["shot"]["xg"]
    if xg < BUILD_MIN_XG:
        return Plan(0.0, LEAD_S, 0, "none")
    # Same intensity as Stage 3: tension (B's xG-weighted look-ahead) or chance quality, whichever is higher.
    level = round(min(1.0, max(feat["tension_before_shot"] * 0.8, 0.5 + xg)), 2)
    hint = "counter" if regained(feat) else "set_piece" if set_piece(feat) else "danger" if xg >= BIG_XG else "none"
    return Plan(level, LEAD_S, 0, hint)
