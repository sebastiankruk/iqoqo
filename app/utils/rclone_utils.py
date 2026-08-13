# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Utility functions for building and parsing rclone remote target paths."""


def get_rclone_target(remote_spec: str, default_subpath: str, filename: str = "") -> str:
    """Formats an rclone target path string.

    Supports both simple remote names (e.g., 'iqoqo-covers') and full remote paths with
    buckets or subdirectories (e.g., 'iqoqo-covers:iqoqo-covers' or 'my-remote:bucket/folder').

    Args:
        remote_spec: The rclone remote specification from environment or config.
        default_subpath: Subpath or bucket fallback if no path is given in remote_spec.
        filename: Optional filename to append to the target path.

    Returns:
        Formatted rclone target path string.
    """
    remote_spec = remote_spec.strip()
    if ":" in remote_spec:
        base, path = remote_spec.split(":", 1)
        path = path.strip("/")
        if not path:
            target_base = f"{base}:{default_subpath}"
        else:
            target_base = f"{base}:{path}"
    else:
        target_base = f"{remote_spec}:{default_subpath}"

    if filename:
        return f"{target_base.rstrip('/')}/{filename}"
    return target_base
