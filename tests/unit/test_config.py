"""Unit tests for src/edgelab/config.py (STORY-008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from edgelab.config import ConfigError, load_collector_config


def _base_env(**overrides):
    env = {
        "EDGELAB_SEC_USER_AGENT": "edge-lab research contact@example.com",
        "EDGELAB_DATA_DIR": "/tmp/edgelab-data",
    }
    env.update(overrides)
    return env


def test_load_collector_config_with_required_vars_present():
    config = load_collector_config(env=_base_env())
    assert config.sec_user_agent == "edge-lab research contact@example.com"
    assert config.data_dir == Path("/tmp/edgelab-data")


def test_load_collector_config_derives_paths_under_data_dir_by_default():
    config = load_collector_config(env=_base_env())
    assert config.raw_db_path == Path("/tmp/edgelab-data/raw_snapshot.db")
    assert config.event_db_path == Path("/tmp/edgelab-data/event.db")
    assert config.reports_dir == Path("/tmp/edgelab-data/reports")


def test_load_collector_config_individual_overrides_take_precedence():
    config = load_collector_config(
        env=_base_env(
            EDGELAB_RAW_DB_PATH="/other/raw.db",
            EDGELAB_REPORTS_DIR="/other/reports",
        )
    )
    assert config.raw_db_path == Path("/other/raw.db")
    assert config.reports_dir == Path("/other/reports")
    # Untouched override still derives from data_dir.
    assert config.event_db_path == Path("/tmp/edgelab-data/event.db")


@pytest.mark.parametrize("missing_var", ["EDGELAB_SEC_USER_AGENT", "EDGELAB_DATA_DIR"])
def test_load_collector_config_raises_for_each_missing_required_var(missing_var):
    env = _base_env()
    del env[missing_var]
    with pytest.raises(ConfigError, match=missing_var):
        load_collector_config(env=env)


def test_load_collector_config_raises_for_blank_required_var():
    with pytest.raises(ConfigError, match="EDGELAB_SEC_USER_AGENT"):
        load_collector_config(env=_base_env(EDGELAB_SEC_USER_AGENT="   "))
