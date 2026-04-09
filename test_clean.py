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
import re


def clean_video_title(title: str) -> str:
    if not title:
        return ""

    title = title.split(",")[0]
    title = title.split(" - ")[0]
    title = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    title = re.sub(r"(?i)\b(blu-ray|dvd|4k|uhd|import|widescreen|edition|steelbook|used|new|english|language|vhs)\b", "", title)
    title = title.strip(" -:")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


print(clean_video_title("Dvd Donnie Darko Dvd, Used English Language English"))
print(clean_video_title("The Lord of the Rings: The Fellowship of the Ring - Extended Edition"))
print(clean_video_title("Inception [Blu-ray] (4K UHD)"))
