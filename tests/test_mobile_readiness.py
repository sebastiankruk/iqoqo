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
"""Mobile readiness contract verification for upcoming v1.0.0 Capacitor apps."""

from pathlib import Path


def test_mobile_nodeinfo_discovery(client, app):
    """Mobile client discovers server metadata and NodeInfo 2.1 protocol links."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = True

    resp = client.get("/.well-known/nodeinfo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "links" in data
    assert any(link.get("rel") == "http://nodeinfo.diaspora.software/ns/schema/2.1" for link in data["links"])

    # Follow nodeinfo 2.1 link
    nodeinfo_resp = client.get("/api/federation/nodeinfo/2.1")
    assert nodeinfo_resp.status_code == 200
    info = nodeinfo_resp.get_json()
    assert info["version"] == "2.1"
    assert info["software"]["name"] == "iqoqo"
    assert "version" in info["software"]
    assert "protocols" in info
    assert "activitypub" in info["protocols"]


def test_mobile_auth_providers_contract(client):
    """Mobile client queries supported authentication providers during login bootstrap."""
    resp = client.get("/api/auth/providers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "google" in data
    assert isinstance(data["google"], bool)


def test_mobile_cors_preflight_headers(client, app):
    """Mobile client native origin receives preflight headers even when CORS_ENABLED is false."""
    with app.app_context():
        app.config["CORS_ENABLED"] = False

    resp = client.open(
        "/api/auth/providers",
        method="OPTIONS",
        headers={
            "Origin": "capacitor://localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Status can be 200 or 204 for OPTIONS
    assert resp.status_code in (200, 204)
    assert resp.headers.get("Access-Control-Allow-Origin") == "capacitor://localhost"

    # Also check https://localhost on public route /api/public/federation/instance-info
    resp_pub = client.open(
        "/api/public/federation/instance-info",
        method="OPTIONS",
        headers={
            "Origin": "https://localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp_pub.status_code in (200, 204)
    assert resp_pub.headers.get("Access-Control-Allow-Origin") in ("https://localhost", "*")


def test_mobile_platform_routing_parity():
    """Verify Android and iOS native shells enforce identical Next.js route rewriting and flight data interception."""
    repo_root = Path(__file__).resolve().parent.parent
    android_file = repo_root / "frontend" / "android" / "app" / "src" / "main" / "java" / "cc" / "iqoqo" / "app" / "MainActivity.java"
    ios_file = repo_root / "frontend" / "ios" / "App" / "App" / "AppDelegate.swift"
    ios_storyboard = repo_root / "frontend" / "ios" / "App" / "App" / "Base.lproj" / "Main.storyboard"

    assert android_file.is_file(), "Android MainActivity.java must exist"
    assert ios_file.is_file(), "iOS AppDelegate.swift must exist"
    assert ios_storyboard.is_file(), "iOS Main.storyboard must exist"

    android_src = android_file.read_text(encoding="utf-8")
    ios_src = ios_file.read_text(encoding="utf-8")
    storyboard_src = ios_storyboard.read_text(encoding="utf-8")

    # 1. iOS Main.storyboard must use custom ViewController from App module (not unrouted CAPBridgeViewController)
    assert 'customClass="ViewController"' in storyboard_src, "iOS Main.storyboard must reference custom ViewController for dynamic routing"
    assert 'customModule="App"' in storyboard_src, "iOS Main.storyboard must bind ViewController from module App"

    # 2. Both must define NextJSRouter / RouteProcessor with placeholder rewrites
    assert "RouteProcessor" in android_src, "MainActivity must set RouteProcessor"
    assert "NextJSRouter" in ios_src, "AppDelegate must declare NextJSRouter"
    assert (
        "class ViewController: CAPBridgeViewController" in ios_src
    ), "AppDelegate must declare ViewController subclassing CAPBridgeViewController"

    # 3. Dynamic route prefixes parity
    expected_prefixes = {
        "/item/",
        "/manifestation/",
        "/work/",
        "/expression/",
        "/u/",
        "/share/",
    }

    for prefix in expected_prefixes:
        assert f'"{prefix}"' in android_src, f"Android MainActivity missing dynamic prefix {prefix}"
        assert f'"{prefix}"' in ios_src, f"iOS AppDelegate missing dynamic prefix {prefix}"

    # 4. Next.js Flight Data (.txt) placeholder rewrite parity
    assert (
        '".txt"' in android_src and "_placeholder.txt" in android_src
    ), "Android MainActivity must rewrite flight data .txt to _placeholder.txt"
    assert '".txt"' in ios_src and "_placeholder.txt" in ios_src, "iOS AppDelegate must rewrite flight data .txt to _placeholder.txt"

    # 5. HTML placeholder rewrite parity
    assert "_placeholder.html" in android_src, "Android MainActivity must rewrite dynamic paths to _placeholder.html"
    assert "_placeholder.html" in ios_src, "iOS AppDelegate must rewrite dynamic paths to _placeholder.html"

    # 6. Help route and placeholder fallback parity
    assert "/help/" in android_src and "/help/_placeholder.txt" in android_src, "Android MainActivity must handle /help/ fallback"
    assert "/help/" in ios_src and "/help/_placeholder.txt" in ios_src, "iOS AppDelegate must handle /help/ fallback"


def test_mobile_dynamic_routes_cover_nextjs_pages():
    """Verify all Next.js dynamic App Router pages have placeholder params and mobile route coverage."""
    repo_root = Path(__file__).resolve().parent.parent
    app_dir = repo_root / "frontend" / "app"
    android_file = repo_root / "frontend" / "android" / "app" / "src" / "main" / "java" / "cc" / "iqoqo" / "app" / "MainActivity.java"
    ios_file = repo_root / "frontend" / "ios" / "App" / "App" / "AppDelegate.swift"

    android_src = android_file.read_text(encoding="utf-8")
    ios_src = ios_file.read_text(encoding="utf-8")

    dynamic_pages = list(app_dir.glob("**/page.tsx"))
    dynamic_routes = []
    for page_path in dynamic_pages:
        rel = page_path.relative_to(app_dir)
        parts = rel.parts
        dynamic_segments = [p for p in parts[:-1] if p.startswith("[") and p.endswith("]")]
        if dynamic_segments:
            prefix = f"/{parts[0]}/"
            dynamic_routes.append((prefix, page_path))

    assert len(dynamic_routes) >= 5, "Expected dynamic routes in frontend/app/"

    for prefix, page_path in dynamic_routes:
        page_src = page_path.read_text(encoding="utf-8")
        assert "generateStaticParams" in page_src, f"Dynamic page {page_path} must declare generateStaticParams() for Capacitor export"
        assert "_placeholder" in page_src, f"Dynamic page {page_path} generateStaticParams() must supply '_placeholder' slug"

        assert f'"{prefix}"' in android_src, f"Android MainActivity missing dynamic route prefix '{prefix}' for {page_path}"
        assert f'"{prefix}"' in ios_src, f"iOS AppDelegate missing dynamic route prefix '{prefix}' for {page_path}"


def test_mobile_app_icons_present_and_branded():
    """Verify Android and iOS native shells include branded iqoqo launcher icons."""
    from PIL import Image

    repo_root = Path(__file__).resolve().parent.parent

    # 1. Android ic_launcher icons must exist and be branded
    android_icon = repo_root / "frontend" / "android" / "app" / "src" / "main" / "res" / "mipmap-xxhdpi" / "ic_launcher_foreground.png"
    assert android_icon.is_file(), "Android ic_launcher_foreground.png must exist"
    with Image.open(android_icon) as im:
        assert im.size[0] >= 192 and im.size[1] >= 192, "Android icon too small"
        center_pixel = im.getpixel((im.size[0] // 2, im.size[1] // 2))
        assert (
            center_pixel[0] > 180 and center_pixel[1] > 60 and center_pixel[2] < 30
        ), f"Android icon center pixel is {center_pixel}, expected iqoqo orange"

    # 2. iOS AppIcon must exist, be 1024x1024 RGB, and branded
    ios_icon = repo_root / "frontend" / "ios" / "App" / "App" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-512@2x.png"
    assert ios_icon.is_file(), "iOS AppIcon-512@2x.png must exist"
    with Image.open(ios_icon) as im:
        assert im.size == (1024, 1024), "iOS AppIcon must be 1024x1024 universal image"
        assert im.mode == "RGB", "iOS AppIcon must be RGB without alpha transparency"
        center_pixel = im.getpixel((512, 512))
        assert (
            center_pixel[0] > 180 and center_pixel[1] > 60 and center_pixel[2] < 30
        ), f"iOS AppIcon center pixel is {center_pixel}, expected iqoqo orange"
        assert not (center_pixel[0] < 100 and center_pixel[2] > 200), "iOS AppIcon still contains default Capacitor blue logo"

    # 3. iOS Contents.json must be valid
    ios_contents = repo_root / "frontend" / "ios" / "App" / "App" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json"
    assert ios_contents.is_file(), "iOS AppIcon Contents.json must exist"
    contents_text = ios_contents.read_text(encoding="utf-8")
    assert "AppIcon-512@2x.png" in contents_text, "iOS Contents.json must reference AppIcon-512@2x.png"


def test_mobile_native_manifests_and_targets_security():
    """Verify Android and iOS native configuration aligns with security and target baselines."""
    repo_root = Path(__file__).resolve().parent.parent

    # 1. AndroidManifest.xml disables allowBackup
    manifest_file = repo_root / "frontend" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    assert manifest_file.is_file()
    manifest_xml = manifest_file.read_text(encoding="utf-8")
    assert 'android:allowBackup="false"' in manifest_xml

    # 2. variables.gradle enforces minSdkVersion = 26
    vars_file = repo_root / "frontend" / "android" / "variables.gradle"
    assert vars_file.is_file()
    vars_text = vars_file.read_text(encoding="utf-8")
    assert "minSdkVersion = 26" in vars_text

    # 3. Android build.gradle has versionName "1.0.0"
    build_gradle = repo_root / "frontend" / "android" / "app" / "build.gradle"
    assert build_gradle.is_file()
    assert 'versionName "1.0.0"' in build_gradle.read_text(encoding="utf-8")

    # 4. iOS Info.plist has arm64 and no armv7
    plist_file = repo_root / "frontend" / "ios" / "App" / "App" / "Info.plist"
    assert plist_file.is_file()
    plist_text = plist_file.read_text(encoding="utf-8")
    assert "armv7" not in plist_text
    assert "arm64" in plist_text

    # 5. iOS project.pbxproj has MARKETING_VERSION = 1.0.0
    pbxproj_file = repo_root / "frontend" / "ios" / "App" / "App.xcodeproj" / "project.pbxproj"
    assert pbxproj_file.is_file()
    assert "MARKETING_VERSION = 1.0.0;" in pbxproj_file.read_text(encoding="utf-8")

    # 6. Android ExampleInstrumentedTest asserts cc.iqoqo.app
    inst_test = (
        repo_root
        / "frontend"
        / "android"
        / "app"
        / "src"
        / "androidTest"
        / "java"
        / "com"
        / "getcapacitor"
        / "myapp"
        / "ExampleInstrumentedTest.java"
    )
    assert inst_test.is_file()
    inst_text = inst_test.read_text(encoding="utf-8")
    assert '"cc.iqoqo.app"' in inst_text
    assert '"com.getcapacitor.app"' not in inst_text

    # 7. Makefile declares repair-authors in .PHONY
    makefile = repo_root / "Makefile"
    assert makefile.is_file()
    phony_line = next(
        (line for line in makefile.read_text(encoding="utf-8").splitlines() if line.startswith(".PHONY:")),
        "",
    )
    assert "repair-authors" in phony_line
