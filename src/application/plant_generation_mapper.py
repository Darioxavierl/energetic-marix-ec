"""Map live plant generation payloads to static central catalog entries."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict


_STOPWORDS = {
    "central",
    "hidroelectrica",
    "hidroelectrico",
    "hidro",
    "termo",
    "termica",
    "termico",
    "de",
    "del",
    "la",
    "el",
    "ep",
    "celec",
}


def normalize_name(value: str) -> str:
    """Return lowercase ASCII-like normalized text for robust matching."""

    lowered = value.lower().strip()
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFD", lowered) if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^a-z0-9 ]+", " ", no_accents).strip()


def name_tokens(value: str) -> set[str]:
    """Tokenize normalized names dropping generic words."""

    tokens = {token for token in normalize_name(value).split() if token and token not in _STOPWORDS}
    return tokens


def _token_overlap_score(left: str, right: str) -> float:
    left_tokens = name_tokens(left)
    right_tokens = name_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    common = left_tokens.intersection(right_tokens)
    return len(common) / max(len(left_tokens), len(right_tokens))


def map_live_generation_to_centrales(
    centrales: list[dict],
    live_plants: list[dict],
    min_match_score: float = 0.5,
) -> dict[str, float]:
    """Map live plant generation to static centrales; distribute unmatched by type."""

    mapped, _ = map_live_generation_to_centrales_with_diagnostics(
        centrales=centrales,
        live_plants=live_plants,
        min_match_score=min_match_score,
    )
    return mapped


def map_live_generation_to_centrales_with_diagnostics(
    centrales: list[dict],
    live_plants: list[dict],
    min_match_score: float = 0.5,
) -> tuple[dict[str, float], dict]:
    """Map live generation and return diagnostics for matching/distribution quality."""

    generation_by_id = {str(c.get("id")): 0.0 for c in centrales}
    central_type = {str(c.get("id")): str(c.get("type", "")).upper() for c in centrales}
    central_capacity = {
        str(c.get("id")): float(c.get("installed_capacity_mw", 0.0) or 0.0) for c in centrales
    }

    unmatched_pool_by_type: dict[str, float] = defaultdict(float)
    used_ids: set[str] = set()
    direct_matches = 0
    distributed_matches = 0

    for live in live_plants:
        live_name = str(live.get("plant_name", ""))
        live_type = str(live.get("plant_type", "")).upper()
        live_mw = float(live.get("mwh", 0.0) or 0.0)
        if live_mw <= 0.0:
            continue

        candidates = [
            c for c in centrales if str(c.get("type", "")).upper() == live_type and str(c.get("id")) not in used_ids
        ]
        if not candidates:
            unmatched_pool_by_type[live_type] += live_mw
            continue

        best_candidate = None
        best_score = 0.0
        for candidate in candidates:
            score = _token_overlap_score(live_name, str(candidate.get("name", "")))
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate is not None and best_score >= min_match_score:
            cid = str(best_candidate.get("id"))
            generation_by_id[cid] += live_mw
            used_ids.add(cid)
            direct_matches += 1
        else:
            unmatched_pool_by_type[live_type] += live_mw

    # Map generic live renewable type into WIND/SOLAR local catalog by installed capacity.
    renewable_pool = float(unmatched_pool_by_type.pop("RENEWABLE", 0.0) or 0.0)
    if renewable_pool > 0.0:
        renewable_ids = [
            cid for cid, ctype in central_type.items() if ctype in {"WIND", "SOLAR"}
        ]
        renewable_capacity = sum(max(0.0, central_capacity[cid]) for cid in renewable_ids)
        if renewable_capacity > 0.0:
            for cid in renewable_ids:
                share = max(0.0, central_capacity[cid]) / renewable_capacity
                generation_by_id[cid] += renewable_pool * share
                distributed_matches += 1
        else:
            unmatched_pool_by_type["RENEWABLE"] += renewable_pool

    for plant_type, pool_mw in unmatched_pool_by_type.items():
        if pool_mw <= 0.0:
            continue
        type_ids = [cid for cid, ctype in central_type.items() if ctype == plant_type]
        total_capacity = sum(max(0.0, central_capacity[cid]) for cid in type_ids)
        if total_capacity <= 0.0:
            continue

        for cid in type_ids:
            share = max(0.0, central_capacity[cid]) / total_capacity
            generation_by_id[cid] += pool_mw * share
            distributed_matches += 1

    diagnostics = {
        "direct_matches": direct_matches,
        "distributed_matches": distributed_matches,
        "unmatched_pool_by_type": {k: float(v) for k, v in unmatched_pool_by_type.items() if float(v) > 0.0},
    }
    return generation_by_id, diagnostics


def calculate_plant_utilization(
    generation_by_id_mw: dict[str, float],
    installed_by_id_mw: dict[str, float],
) -> dict[str, float]:
    """Calculate normalized utilization per central id."""

    utilization: dict[str, float] = {}
    for cid, installed in installed_by_id_mw.items():
        generated = max(0.0, generation_by_id_mw.get(cid, 0.0))
        installed_safe = max(0.0, installed)
        if installed_safe <= 0.0:
            utilization[cid] = 0.0
            continue
        utilization[cid] = min(1.0, generated / installed_safe)
    return utilization