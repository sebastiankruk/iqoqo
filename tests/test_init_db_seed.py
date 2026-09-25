"""Tests for secure fresh-install seed ownership setup."""

import pytest

from scripts.init_db import _validated_seed_admin


def test_seed_import_requires_explicit_admin_email(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "")
    app.config["ADMIN_EMAIL"] = "admin@iqoqo.local"
    app.config["ADMIN_PASSWORD"] = "strong-test-password"

    with pytest.raises(ValueError, match="explicit ADMIN_EMAIL"):
        _validated_seed_admin(app)


@pytest.mark.parametrize("email", ["not-an-email", "admin@example.com", "admin@instance.local"])
def test_seed_import_rejects_invalid_or_placeholder_admin_email(app, monkeypatch, email):
    monkeypatch.setenv("ADMIN_EMAIL", email)
    app.config["ADMIN_EMAIL"] = email
    app.config["ADMIN_PASSWORD"] = "strong-test-password"

    with pytest.raises(ValueError, match="ADMIN_EMAIL"):
        _validated_seed_admin(app)


def test_seed_import_accepts_explicit_valid_admin_credentials(app, monkeypatch):
    admin_email = "bootstrap-admin@iqoqo.cc"
    admin_password = "strong-test-password"
    monkeypatch.setenv("ADMIN_EMAIL", admin_email)
    app.config["ADMIN_EMAIL"] = admin_email
    app.config["ADMIN_PASSWORD"] = admin_password

    assert _validated_seed_admin(app) == (admin_email, admin_password)


def test_seed_import_rejects_weak_bootstrap_admin_password(app, monkeypatch):
    admin_email = "bootstrap-admin@iqoqo.cc"
    monkeypatch.setenv("ADMIN_EMAIL", admin_email)
    app.config["ADMIN_EMAIL"] = admin_email
    app.config["ADMIN_PASSWORD"] = "short"

    with pytest.raises(ValueError, match="at least 8 characters"):
        _validated_seed_admin(app)
