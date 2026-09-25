"""Unit tests for src/edgelab/config.py (STORY-008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from edgelab.config import ConfigError, load_collector_config, load_notification_config


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


def test_load_notification_config_enabled_when_both_vars_present():
    config = load_notification_config(
        env={
            "EDGELAB_TELEGRAM_BOT_TOKEN": "123:abc",
            "EDGELAB_TELEGRAM_CHAT_ID": "456",
        }
    )
    assert config.telegram_enabled is True
    assert config.telegram_bot_token == "123:abc"
    assert config.telegram_chat_id == "456"


def test_load_notification_config_disabled_when_env_empty():
    config = load_notification_config(env={})
    assert config.telegram_enabled is False
    assert config.telegram_bot_token is None
    assert config.telegram_chat_id is None


@pytest.mark.parametrize(
    "present_var",
    ["EDGELAB_TELEGRAM_BOT_TOKEN", "EDGELAB_TELEGRAM_CHAT_ID"],
)
def test_load_notification_config_disabled_when_only_one_var_present(present_var):
    config = load_notification_config(env={present_var: "some-value"})
    assert config.telegram_enabled is False


def test_load_collector_config_derives_price_db_path_by_default():
    config = load_collector_config(env=_base_env())
    assert config.price_db_path == Path("/tmp/edgelab-data/price_daily.db")


def test_load_collector_config_price_db_path_override_takes_precedence():
    config = load_collector_config(
        env=_base_env(EDGELAB_PRICE_DB_PATH="/other/prices.db")
    )
    assert config.price_db_path == Path("/other/prices.db")
