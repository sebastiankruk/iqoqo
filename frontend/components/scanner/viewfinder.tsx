// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import { getMediaMetadata } from "@/lib/media";
import { MediaFormat, ScanFormat } from "@/types/frbr";

/**
 * Viewfinder overlay with corner brackets and animated scanning line.
 *
 * @param {object} props The component props
 * @param {boolean} [props.isScanning=true] Whether the line should animate
 * @param {MediaFormat | ScanFormat} [props.format="book"] Media format for aspect ratio
 * @returns {JSX.Element} The component
 */
export function Viewfinder({
  isScanning = true,
  format = "book",
}: {
  isScanning?: boolean;
  format?: MediaFormat | ScanFormat;
}) {
  const metadata = getMediaMetadata(format);

  // Dimensions: Books are vertical 2:3, others (CDs/Vinyls/Video/BoardGame) are square 1:1
  const width = 240;
  const height = width / metadata.aspectRatio;

  const bracketSize = 28;
  const strokeWidth = 3;

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      {/* Darkened overlay with transparent cutout */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 bg-black/60" style={{ bottom: `calc(50% + ${height / 2}px)` }} />
        <div className="absolute inset-x-0 bottom-0 bg-black/60" style={{ top: `calc(50% + ${height / 2}px)` }} />
        <div
          className="absolute top-1/2 bottom-1/2 left-0 bg-black/60"
          style={{
            marginTop: `-${height / 2}px`,
            marginBottom: `-${height / 2}px`,
            width: `calc(50% - ${width / 2}px)`,
          }}
        />
        <div
          className="absolute top-1/2 bottom-1/2 right-0 bg-black/60"
          style={{
            marginTop: `-${height / 2}px`,
            marginBottom: `-${height / 2}px`,
            width: `calc(50% - ${width / 2}px)`,
          }}
        />
      </div>

      {/* Viewfinder box */}
      <div style={{ width, height }} className="relative" data-testid="viewfinder-box">
        {/* Corner brackets */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox={`0 0 ${width} ${height}`}
          fill="none"
          role="presentation"
        >
          <path
            d={`M ${strokeWidth / 2} ${bracketSize} L ${strokeWidth / 2} ${strokeWidth / 2} L ${bracketSize} ${strokeWidth / 2}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${width - bracketSize} ${strokeWidth / 2} L ${width - strokeWidth / 2} ${strokeWidth / 2} L ${width - strokeWidth / 2} ${bracketSize}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${strokeWidth / 2} ${height - bracketSize} L ${strokeWidth / 2} ${height - strokeWidth / 2} L ${bracketSize} ${height - strokeWidth / 2}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${width - bracketSize} ${height - strokeWidth / 2} L ${width - strokeWidth / 2} ${height - strokeWidth / 2} L ${width - strokeWidth / 2} ${height - bracketSize}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* Scanning line */}
        {isScanning && (
          <div className="absolute inset-x-2 animate-[scan-line_2.5s_ease-in-out_infinite]">
            <div className="h-0.5 w-full bg-accent shadow-[0_0_8px_hsl(24_100%_41%)]" />
          </div>
        )}
      </div>
    </div>
  );
}
