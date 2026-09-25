"""Well-formedness checks for the deploy/ systemd units (STORY-008).

This sandbox is macOS with no systemd, so `systemd-analyze verify`
cannot run here -- these tests check only that the files parse as
well-formed INI (systemd unit syntax is INI-compatible) and contain
the specific directives docs/04-infrastructure.md requires. Real
validation against systemd itself is explicitly deferred to
deploy/install.sh running on the actual Pi.
"""

from __future__ import annotations

import configparser
from pathlib import Path

DEPLOY_DIR = Path(__file__).resolve().parents[2] / "deploy"


def _parse(name: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False)
    # systemd allows repeated keys in some sections; keep this test
    # only as a syntax check, not a systemd semantics check.
    parser.optionxform = str
    parser.read(DEPLOY_DIR / name)
    return parser


def test_service_unit_is_well_formed_ini():
    parser = _parse("edgelab-8k-poll.service")
    assert "Unit" in parser
    assert "Service" in parser
    assert parser["Unit"]["RequiresMountsFor"] == "/mnt/data"
    assert parser["Service"]["EnvironmentFile"].startswith("-")
    assert "MemoryMax" in parser["Service"]


def test_timer_unit_is_well_formed_ini():
    parser = _parse("edgelab-8k-poll.timer")
    assert "Timer" in parser
    assert "America/New_York" in parser["Timer"]["OnCalendar"]
    assert parser["Install"]["WantedBy"] == "timers.target"


def test_install_and_uninstall_scripts_exist_and_are_executable():
    install = DEPLOY_DIR / "install.sh"
    uninstall = DEPLOY_DIR / "uninstall.sh"
    assert install.exists() and install.stat().st_mode & 0o111
    assert uninstall.exists() and uninstall.stat().st_mode & 0o111
    # Uninstall must never remove anything under /mnt/data -- a
    # cheap, blunt but meaningful safety check on the actual script
    # text: no line that mentions /mnt/data may also contain "rm".
    for line in uninstall.read_text().splitlines():
        if "/mnt/data" in line:
            assert "rm" not in line, f"uninstall.sh must never rm anything under /mnt/data: {line!r}"
