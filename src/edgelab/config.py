"""Runtime configuration loader.

Single place that reads EDGELAB_* environment variables into a typed
config object, per docs/08-credentials.md's naming convention. A
required variable that is missing or blank raises ConfigError naming
exactly which variable and pointing at that document -- this module
never silently falls back to a default for anything that must be a
deliberate operator choice: a placeholder User-Agent would violate
SEC's fair-access policy, and a wrong or missing data directory risks
silently writing collected evidence to the wrong disk (or nowhere,
if EDGELAB_DATA_DIR is unset and a relative default is used without
the operator noticing which directory that resolves to on the Pi).

Story: stories/STORY-008-pi-collector-entrypoint.md
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


class ConfigError(RuntimeError):
    """A required EDGELAB_* environment variable is missing or blank."""


@dataclass(frozen=True)
class CollectorConfig:
    sec_user_agent: str
    data_dir: Path
    raw_db_path: Path
    event_db_path: Path
    reports_dir: Path
    universe_path: Path


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if value is None or not value.strip():
        raise ConfigError(
            f"{name} is not set. Set it in .env on this machine "
            "(see docs/08-credentials.md) before running any collector -- "
            "it is never given a silent default."
        )
    return value.strip()


def _optional_path(env: Mapping[str, str], name: str, default: Path) -> Path:
    value = env.get(name)
    if value is None or not value.strip():
        return default
    return Path(value.strip()).expanduser()


def load_collector_config(*, env: Optional[Mapping[str, str]] = None) -> CollectorConfig:
    """Build a CollectorConfig from environment variables.

    `env` defaults to the real process environment but is injectable
    so tests never need to mutate os.environ (and never risk a test
    accidentally reading a developer's real .env).
    """
    resolved_env: Mapping[str, str] = os.environ if env is None else env

    sec_user_agent = _require(resolved_env, "EDGELAB_SEC_USER_AGENT")
    data_dir = Path(_require(resolved_env, "EDGELAB_DATA_DIR")).expanduser()

    raw_db_path = _optional_path(
        resolved_env, "EDGELAB_RAW_DB_PATH", data_dir / "raw_snapshot.db"
    )
    event_db_path = _optional_path(
        resolved_env, "EDGELAB_EVENT_DB_PATH", data_dir / "event.db"
    )
    reports_dir = _optional_path(resolved_env, "EDGELAB_REPORTS_DIR", data_dir / "reports")
    universe_path = _optional_path(
        resolved_env, "EDGELAB_UNIVERSE_PATH", Path("config") / "universe.csv"
    )

    return CollectorConfig(
        sec_user_agent=sec_user_agent,
        data_dir=data_dir,
        raw_db_path=raw_db_path,
        event_db_path=event_db_path,
        reports_dir=reports_dir,
        universe_path=universe_path,
    )
