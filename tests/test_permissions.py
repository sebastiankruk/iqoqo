import re
from app.core import permissions as perms


def test_permissions_yaml_matches_enum():
    with open("shared/permissions.yaml", "r") as f:
        text = f.read()
    # Naive extraction to avoid PyYAML as a test dependency in CI
    names = set(re.findall(r"^\s*-\s+name:\s*(\S+)$", text, flags=re.M))
    enum_values = {m.value for m in perms.ItemPermissions}
    assert names.issubset(enum_values)
