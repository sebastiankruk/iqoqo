"""Tests for the web interface routes and static files."""

import os


def test_index_page(client):
    """Test that the index page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<sub>i</sub>QO<sup>2</sup>" in response.data


def test_scan_page(client):
    """Test that the scan page loads."""
    response = client.get("/scan")
    assert response.status_code == 200
    assert b"reader" in response.data


def test_add_page(client):
    """Test that the add page loads."""
    response = client.get("/add")
    assert response.status_code == 200
    assert b"fiIsbnValue" in response.data


def test_update_page(client):
    """Test that the update page loads."""
    response = client.get("/update")
    assert response.status_code == 200
    assert b"fiIsbnValue" in response.data


def test_list_books_page(client):
    """Test that the list books page loads."""
    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"ISBN" in response.data
    assert b"Title" in response.data


def test_static_css_bootstrap(client):
    """Test that Bootstrap CSS file is accessible."""
    response = client.get("/static/css/bootstrap.min.css")
    assert response.status_code == 200
    assert response.content_type.startswith("text/css")


def test_static_css_base(client):
    """Test that base CSS file is accessible."""
    response = client.get("/static/css/base.css")
    assert response.status_code == 200
    assert response.content_type.startswith("text/css")


def test_static_js_jquery(client):
    """Test that jQuery file is accessible."""
    response = client.get("/static/js/jquery-3.6.0.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_bootstrap(client):
    """Test that Bootstrap JS file is accessible."""
    response = client.get("/static/js/bootstrap.bundle.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_html5_qrcode(client):
    """Test that html5-qrcode library is accessible."""
    response = client.get("/static/js/html5-qrcode.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_isbn(client):
    """Test that custom ISBN JS file is accessible."""
    response = client.get("/static/js/isbn.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_beep(client):
    """Test that custom beep JS file is accessible."""
    response = client.get("/static/js/beep.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_toast(client):
    """Test that custom toast JS file is accessible."""
    response = client.get("/static/js/toast.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_metaform(client):
    """Test that custom metaform JS file is accessible."""
    response = client.get("/static/js/metaform.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_update_buttons(client):
    """Test that custom update_buttons JS file is accessible."""
    response = client.get("/static/js/update_buttons.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_qrcode(client):
    """Test that custom qrcode JS file is accessible."""
    response = client.get("/static/js/qrcode.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_add_update(client):
    """Test that custom add_update JS file is accessible."""
    response = client.get("/static/js/add_update.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_audio_ding(client):
    """Test that ding audio file is accessible."""
    response = client.get("/static/audio/ding.mp3")
    assert response.status_code == 200
    assert response.content_type.startswith("audio/")


def test_static_audio_error(client):
    """Test that error audio file is accessible."""
    response = client.get("/static/audio/error2.mp3")
    assert response.status_code == 200
    assert response.content_type.startswith("audio/")


def test_index_includes_static_assets(client):
    """Test that the index page includes references to static assets."""
    response = client.get("/")
    assert response.status_code == 200

    # Check for CSS links
    assert b"bootstrap.min.css" in response.data
    assert b"base.css" in response.data

    # Check for JS script tags
    assert b"bootstrap.bundle.min.js" in response.data
    assert b"jquery-3.6.0.min.js" in response.data
    assert b"html5-qrcode.min.js" in response.data
    assert b"beep.js" in response.data
    assert b"isbn.js" in response.data


def test_scan_page_includes_scanner_scripts(client):
    """Test that the scan page includes scanner-related scripts."""
    response = client.get("/scan")
    assert response.status_code == 200

    # Check for scanner-specific scripts
    assert b"qrcode.js" in response.data
    assert b"metaform.js" in response.data
    assert b"update_buttons.js" in response.data


def test_add_page_includes_form_scripts(client):
    """Test that the add page includes form-related scripts."""
    response = client.get("/add")
    assert response.status_code == 200

    # Check for form-specific scripts
    assert b"add_update.js" in response.data
    assert b"metaform.js" in response.data
    assert b"update_buttons.js" in response.data


def test_static_files_exist_on_filesystem(app):
    """Test that expected static files exist in the filesystem."""
    static_folder = os.path.join(app.root_path, "web", "static")

    # Check CSS files
    assert os.path.exists(os.path.join(static_folder, "css", "bootstrap.min.css"))
    assert os.path.exists(os.path.join(static_folder, "css", "base.css"))

    # Check JS files
    assert os.path.exists(os.path.join(static_folder, "js", "jquery-3.6.0.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "bootstrap.bundle.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "html5-qrcode.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "isbn.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "beep.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "toast.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "metaform.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "update_buttons.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "qrcode.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "add_update.js"))

    # Check audio files
    assert os.path.exists(os.path.join(static_folder, "audio", "ding.mp3"))
    assert os.path.exists(os.path.join(static_folder, "audio", "error2.mp3"))
