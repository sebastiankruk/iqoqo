import json
import tomllib
from pathlib import Path


def test_versions_are_in_sync() -> None:
    """
    Ensure that the version in pyproject.toml matches the version in package.json.
    """
    root_dir = Path(__file__).parents[1]

    # Read pyproject.toml
    with open(root_dir / "pyproject.toml", "rb") as f:
        pyproject_data = tomllib.load(f)
        py_version = pyproject_data["project"]["version"]

    # Read package.json
    with open(root_dir / "package.json", "r", encoding="utf-8") as f:
        package_data = json.load(f)
        js_version = package_data["version"]

    assert py_version == js_version, f"Version mismatch: pyproject.toml has {py_version}, " f"but package.json has {js_version}."
