"""Local app settings (persisted volume), the decoupled-app replacement for
reading ``knowledge_base.map_paths`` out of the monolith's shared aw.json.

One small JSON file under the persistent data volume — the whole settings
surface today is just ``map_paths``, so a dedicated file beats inventing a
generic config store for one key.
"""

from __future__ import annotations

import json
import os

DATA_DIR = os.environ.get("KB_DATA_DIR", "/app/data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

#: Seeded on a FRESH install only (no settings file yet). The workspace's
#: repos/ dir is the one thing worth indexing that the workspace folder map
#: does not already cover, and it is mounted here as $AW_WORKSPACE_REPOS, so
#: a new workspace gets a useful KB without anyone configuring anything.
#:
#: Only a default: once the file exists this is never re-applied, so removing
#: the entry in the UI sticks.
DEFAULT_MAP_PATHS = [
    os.path.join(os.environ.get("AW_WORKSPACE_CONTAINER_DIR", "/opt/aw-workspace"), "repos"),
]


def get_settings() -> dict:
    fresh = False
    try:
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
        fresh = True
    data.setdefault("map_paths", list(DEFAULT_MAP_PATHS) if fresh else [])
    # Workspace folders the user switched OFF. Stored as an opt-OUT so the
    # workspace stays the source of truth for what EXISTS: a folder mapped
    # later is indexed by default, and this file only ever records the
    # exceptions. An opt-in list would silently ignore new folders.
    data.setdefault("disabled_folders", [])
    return data


def save_settings(data: dict) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    current = get_settings()
    current.update(data)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(current, f, indent=2)
    return current


#: Query-time ranking weights (card 4235bf3b). Applied at SEARCH time over the
#: over-fetched candidate pool, so retuning is a settings.json edit under the
#: ``ranking`` key, never a reindex. ``recency_floor`` 1.0 switches recency off.
DEFAULT_RANKING = {
    "curated_weight": 1.05,
    "legacy_weight": 0.85,
    # A doc id containing "/<root>/" is a copy of a deactivated codebase.
    "legacy_roots": ["repos/agentic-workspace"],
    # Top-level KB folders whose docs are curated, hand-written knowledge.
    "curated_top_dirs": ["docs", "skills", "memory", "apps"],
    "recency_floor": 0.85,
    "recency_half_life_days": 180,
    # Age assumed for a doc with no modified_at (unbackfilled row).
    "default_age_days": 30,
    "pool_min": 60,
    "pool_factor": 12,
}


def get_ranking() -> dict:
    """Defaults overlaid with the optional ``ranking`` dict in settings.json."""
    out = dict(DEFAULT_RANKING)
    override = get_settings().get("ranking")
    if isinstance(override, dict):
        out.update({k: v for k, v in override.items() if k in DEFAULT_RANKING})
    return out
