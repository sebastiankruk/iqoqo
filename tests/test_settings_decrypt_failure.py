"""Tests for the InstanceSettings read path under SECRET_KEY rotation.

A rotated SECRET_KEY makes every Fernet-encrypted row undecryptable. The
behaviour under test is what happens next, because the previous behaviour
(returning the stored envelope) handed callers a dict that they then used as
if it were the credential.
"""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

from __future__ import annotations

import sys

import pytest

# `app.db` is the Flask-SQLAlchemy instance, which shadows the `app.db`
# package attribute, so `import app.db.settings` cannot resolve. Go through
# sys.modules instead.
settings_mod = sys.modules["app.db.settings"]

from app.db import db  # noqa: E402
from app.db.settings import (  # noqa: E402
    InstanceSettings,
    decrypt_setting_value,
    encrypt_setting_value,
    is_sensitive_key,
    normalise_setting_value,
)

ENVELOPE = {"_encrypted": True, "ciphertext": "gAAAAA-not-a-real-token"}


# ---------------------------------------------------------------------------
# Decrypt failure is unset, not the envelope
# ---------------------------------------------------------------------------


def rotated_cipher():
    """A real Fernet built from a *different* key, so decrypt() raises InvalidToken.

    Simulating the rotation properly matters: the code path under test catches
    InvalidToken specifically, and a stub that raised RuntimeError would not
    exercise it at all.
    """
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(b"a-totally-different-secret").digest())
    return Fernet(key)


def test_decrypt_failure_returns_none_not_the_envelope(monkeypatch):
    """A rotated key must not produce a dict masquerading as a value."""
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    assert decrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", dict(ENVELOPE)) is None


def test_get_value_returns_the_caller_default_when_decryption_fails(app, monkeypatch):
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    db.session.add(InstanceSettings(key="OPENOBSERVE_RUM_CLIENT_TOKEN", value=dict(ENVELOPE)))
    db.session.commit()

    # Without the default-honouring fix this would be None.
    assert InstanceSettings.get_value("OPENOBSERVE_RUM_CLIENT_TOKEN", "fallback") == "fallback"


def test_get_value_returns_none_with_no_default_when_decryption_fails(app, monkeypatch):
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    db.session.add(InstanceSettings(key="OPENOBSERVE_RUM_CLIENT_TOKEN", value=dict(ENVELOPE)))
    db.session.commit()
    assert InstanceSettings.get_value("OPENOBSERVE_RUM_CLIENT_TOKEN") is None


# ---------------------------------------------------------------------------
# Legacy plaintext rows still read
# ---------------------------------------------------------------------------


def test_plaintext_value_is_returned_unchanged():
    assert decrypt_setting_value("SOME_KEY", "plain-text") == "plain-text"


def test_non_envelope_dict_is_returned_unchanged():
    payload = {"not": "an envelope"}
    assert decrypt_setting_value("SOME_KEY", payload) == payload


def test_round_trip_still_works():
    token = "a-perfectly-fine-token-value-123"
    encrypted = encrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", token)
    assert isinstance(encrypted, dict)
    assert encrypted["_encrypted"] is True
    assert decrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", encrypted) == token


def test_a_stored_envelope_is_not_re_encrypted():
    assert encrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", dict(ENVELOPE)) == ENVELOPE


# ---------------------------------------------------------------------------
# Shape validation on read
# ---------------------------------------------------------------------------


def test_rum_token_key_is_already_encrypted_at_rest():
    """No scheme change was needed: _TOKEN is already matched."""
    assert is_sensitive_key("OPENOBSERVE_RUM_CLIENT_TOKEN")


@pytest.mark.parametrize(
    "value",
    [None, 12345, {"nested": "object"}, ["list"], "short", "", "has spaces and $dollars", "a" * 513],
)
def test_malformed_browser_token_is_treated_as_unset(value):
    assert normalise_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", value) is None


def test_well_formed_browser_token_passes_through():
    token = "SENTINEL-RUM-TOKEN-a1b2c3d4e5f6g7h8"
    assert normalise_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", token) == token


def test_other_keys_are_not_shape_checked():
    """Only browser-bound tokens are validated; other settings keep their types."""
    assert normalise_setting_value("SOME_LIST_KEY", [1, 2, 3]) == [1, 2, 3]
    assert normalise_setting_value("SOME_INT_KEY", 42) == 42


def test_ciphertext_envelope_never_reaches_the_browser(app, monkeypatch):
    """The end-to-end invariant: what get_value returns is a usable token."""
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    db.session.add(InstanceSettings(key="OPENOBSERVE_RUM_CLIENT_TOKEN", value=dict(ENVELOPE)))
    db.session.commit()

    value = InstanceSettings.get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")
    assert value is None
    assert not isinstance(value, dict)


# ---------------------------------------------------------------------------
# Cross-key confusion
# ---------------------------------------------------------------------------


def test_storing_under_one_key_and_reading_under_another_yields_unset(app, monkeypatch):
    """A row written under a sensitive key must not decrypt under a different one."""
    real = settings_mod._get_fernet_cipher
    # Encrypt under the current key...
    envelope = encrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", "SENTINEL-RUM-TOKEN-a1b2c3d4")

    # ...then simulate a rotation, which invalidates every stored envelope.
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    assert decrypt_setting_value("OPENOBSERVE_RUM_CLIENT_TOKEN", envelope) is None
    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", real)


def test_startup_drift_probe_logs_aggregated_error_without_leaking_secret(app, monkeypatch, caplog):
    """Startup drift probe logs one aggregated ERROR naming keys only and leaves rows intact."""
    import logging

    from app.db.settings import check_encrypted_settings_drift

    secret_val = "SENTINEL-SUPER-SECRET-OAUTH-VALUE"
    envelope = encrypt_setting_value("GOOGLE_CLIENT_SECRET", secret_val)
    db.session.add(InstanceSettings(key="GOOGLE_CLIENT_SECRET", value=dict(envelope)))
    db.session.add(InstanceSettings(key="DISCOGS_API_TOKEN", value=dict(ENVELOPE)))
    db.session.commit()

    monkeypatch.setattr(settings_mod, "_get_fernet_cipher", rotated_cipher)
    with caplog.at_level(logging.ERROR):
        failed = check_encrypted_settings_drift(app.logger)

    assert sorted(failed) == ["DISCOGS_API_TOKEN", "GOOGLE_CLIENT_SECRET"]
    error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_msgs) == 1
    assert "DISCOGS_API_TOKEN" in error_msgs[0]
    assert "GOOGLE_CLIENT_SECRET" in error_msgs[0]
    assert "make migrate-secrets" in error_msgs[0]
    assert secret_val not in error_msgs[0]
    assert envelope["ciphertext"] not in error_msgs[0]

    # Rows remain untouched in DB so restoring ENV_FILE recovers them
    stored_row = db.session.execute(db.select(InstanceSettings).filter_by(key="GOOGLE_CLIENT_SECRET")).scalar_one()
    assert stored_row.value == envelope
