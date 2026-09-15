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
"""QR code SVG and PNG generation utilities."""

import io
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import defusedxml.ElementTree as SafeET
import qrcode
import qrcode.image.svg
from PIL import ImageDraw

logger = logging.getLogger(__name__)

DEFAULT_LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "resources" / "images" / "iqoqo-logo.svg"


def generate_item_qrcode(
    item_id: int,  # pylint: disable=unused-argument
    item_url: str,
    img_format: str = "png",
    logo_path: str | Path | None = None,
) -> tuple[io.BytesIO, str]:
    """Generate a branded QR code for an item URL in PNG or SVG format.

    Args:
        item_id: Unique identifier for the item (reserved for telemetry/correlation).
        item_url: Target URL encoded into the QR code matrix.
        img_format: Format identifier ('svg' or 'png').
        logo_path: Optional path to custom SVG logo overlay.

    Returns:
        tuple[io.BytesIO, str]: In-memory byte stream and matching MIME type.
    """
    if logo_path is None:
        logo_path = DEFAULT_LOGO_PATH

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(item_url)
    qr.make(fit=True)

    normalized_format = img_format.lower().strip()

    if normalized_format == "svg":
        return _render_svg_qrcode(qr, logo_path)

    return _render_png_qrcode(qr, logo_path)


def _render_svg_qrcode(qr: qrcode.QRCode, logo_path: str | Path) -> tuple[io.BytesIO, str]:
    """Render QR code matrix as SVG with branded center logo."""
    img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
    root = img._img  # pylint: disable=protected-access

    width_str = root.get("width", "290")
    width_match = re.search(r"[\d.]+", width_str)
    width = float(width_match.group(0)) if width_match else 290.0
    center_x = width / 2.0
    center_y = width / 2.0
    logo_size = width * 0.22
    padding = width * 0.02

    rect_size = logo_size + 2 * padding
    rect_x = center_x - rect_size / 2.0
    rect_y = center_y - rect_size / 2.0

    rect = ET.Element(
        "rect",
        x=str(rect_x),
        y=str(rect_y),
        width=str(rect_size),
        height=str(rect_size),
        fill="white",
    )
    root.append(rect)

    try:
        with open(logo_path, encoding="utf-8") as f:
            logo_svg = f.read()

        root_logo = SafeET.fromstring(logo_svg)
        path_el_logo = None
        for el in root_logo.iter():
            if el.tag.endswith("path"):
                path_el_logo = el
                break

        if path_el_logo is not None:
            d_attr = path_el_logo.get("d")
            if d_attr:
                scale = logo_size / 200.0
                offset_x = center_x - logo_size / 2.0
                offset_y = center_y - logo_size / 2.0

                path_el = ET.Element(
                    "path",
                    d=d_attr,
                    fill="#d15500",
                    transform=f"translate({offset_x},{offset_y}) scale({scale})",
                )
                root.append(path_el)
    except (ET.ParseError, OSError, AttributeError, ValueError, KeyError) as e:
        logger.error("Failed to embed logo in SVG QR code: %s", e)

    img_io = io.BytesIO()
    img.save(img_io)
    img_io.seek(0)
    return img_io, "image/svg+xml"


def _render_png_qrcode(qr: qrcode.QRCode, logo_path: str | Path) -> tuple[io.BytesIO, str]:
    """Render QR code matrix as PNG with branded center logo overlay."""
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    width, height = img.size
    center_x = width // 2
    center_y = height // 2
    logo_size = int(width * 0.22)
    padding = int(width * 0.02)

    draw = ImageDraw.Draw(img)
    half_rect = (logo_size + 2 * padding) // 2
    draw.rectangle(
        [center_x - half_rect, center_y - half_rect, center_x + half_rect, center_y + half_rect],
        fill="white",
    )

    try:
        with open(logo_path, encoding="utf-8") as f:
            logo_svg = f.read()

        root_logo = SafeET.fromstring(logo_svg)
        path_el_logo = None
        for el in root_logo.iter():
            if el.tag.endswith("path"):
                path_el_logo = el
                break

        if path_el_logo is not None:
            d_attr = path_el_logo.get("d")
            if d_attr:
                tokens = re.findall(r"([a-zA-Z])|([-+]?\d*\.\d+|[-+]?\d+)", d_attr)
                commands: list[tuple[str, list[float]]] = []
                for cmd, val in tokens:
                    if cmd:
                        commands.append((cmd, []))
                    elif val and commands:
                        commands[-1][1].append(float(val))

                polygons: list[list[tuple[float, float]]] = []
                current_polygon: list[tuple[float, float]] = []
                cx, cy = 0.0, 0.0
                start_x, start_y = 0.0, 0.0

                for cmd, args in commands:
                    if cmd == "M":
                        if current_polygon:
                            polygons.append(current_polygon)
                        cx, cy = args[0], args[1]
                        start_x, start_y = cx, cy
                        current_polygon = [(cx, cy)]
                        for idx in range(2, len(args), 2):
                            cx, cy = args[idx], args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "m":
                        if current_polygon:
                            polygons.append(current_polygon)
                        cx += args[0]
                        cy += args[1]
                        start_x, start_y = cx, cy
                        current_polygon = [(cx, cy)]
                        for idx in range(2, len(args), 2):
                            cx += args[idx]
                            cy += args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "L":
                        for idx in range(0, len(args), 2):
                            cx, cy = args[idx], args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "l":
                        for idx in range(0, len(args), 2):
                            cx += args[idx]
                            cy += args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd in ("c", "C"):
                        is_rel = cmd == "c"
                        for idx in range(0, len(args), 6):
                            dx1, dy1, dx2, dy2, dx, dy = args[idx : idx + 6]
                            x1 = (cx + dx1) if is_rel else dx1
                            y1 = (cy + dy1) if is_rel else dy1
                            x2 = (cx + dx2) if is_rel else dx2
                            y2 = (cy + dy2) if is_rel else dy2
                            x3 = (cx + dx) if is_rel else dx
                            y3 = (cy + dy) if is_rel else dy
                            steps = 5
                            for s in range(1, steps + 1):
                                t = s / steps
                                b0 = (1 - t) ** 3
                                b1 = 3 * ((1 - t) ** 2) * t
                                b2 = 3 * (1 - t) * (t**2)
                                b3 = t**3
                                px = b0 * cx + b1 * x1 + b2 * x2 + b3 * x3
                                py = b0 * cy + b1 * y1 + b2 * y2 + b3 * y3
                                current_polygon.append((px, py))
                            cx, cy = x3, y3
                    elif cmd in ("z", "Z"):
                        if current_polygon:
                            current_polygon.append((start_x, start_y))
                            polygons.append(current_polygon)
                            current_polygon = []
                        cx, cy = start_x, start_y

                if current_polygon:
                    polygons.append(current_polygon)

                scale = logo_size / 200.0
                offset_x = center_x - logo_size / 2.0
                offset_y = center_y - logo_size / 2.0

                for p_idx, poly in enumerate(polygons):
                    scaled_poly = [(offset_x + x * scale, offset_y + y * scale) for x, y in poly]
                    if len(scaled_poly) >= 3:
                        color = "white" if p_idx in (1, 5, 7) else "#d15500"
                        draw.polygon(scaled_poly, fill=color)
    except (ET.ParseError, OSError, AttributeError, ValueError, KeyError) as e:
        logger.error("Failed to embed logo in PNG QR code: %s", e)

    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)
    return img_io, "image/png"
