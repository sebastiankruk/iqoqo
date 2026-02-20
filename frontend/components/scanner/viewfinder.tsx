/** Viewfinder overlay with corner brackets and animated scanning line. */
export function Viewfinder() {
  const bracketSize = 28;
  const strokeWidth = 3;

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      {/* Darkened overlay with transparent cutout */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-x-0 top-0 bottom-1/2 mb-[120px] bg-black/50" />
        <div className="absolute inset-x-0 top-1/2 bottom-0 mt-[120px] bg-black/50" />
        <div className="absolute top-1/2 bottom-1/2 left-0 -mt-[120px] -mb-[120px] w-[calc(50%-120px)] bg-black/50" />
        <div className="absolute top-1/2 bottom-1/2 right-0 -mt-[120px] -mb-[120px] w-[calc(50%-120px)] bg-black/50" />
      </div>

      {/* Viewfinder box */}
      <div className="relative h-[240px] w-[240px]">
        {/* Corner brackets */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 240 240"
          fill="none"
          aria-hidden="true"
        >
          <path
            d={`M ${strokeWidth / 2} ${bracketSize} L ${strokeWidth / 2} ${strokeWidth / 2} L ${bracketSize} ${strokeWidth / 2}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${240 - bracketSize} ${strokeWidth / 2} L ${240 - strokeWidth / 2} ${strokeWidth / 2} L ${240 - strokeWidth / 2} ${bracketSize}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${strokeWidth / 2} ${240 - bracketSize} L ${strokeWidth / 2} ${240 - strokeWidth / 2} L ${bracketSize} ${240 - strokeWidth / 2}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={`M ${240 - bracketSize} ${240 - strokeWidth / 2} L ${240 - strokeWidth / 2} ${240 - strokeWidth / 2} L ${240 - strokeWidth / 2} ${240 - bracketSize}`}
            stroke="white"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* Scanning line */}
        <div className="absolute inset-x-2 animate-[scan-line_2.5s_ease-in-out_infinite]">
          <div className="h-0.5 w-full bg-accent shadow-[0_0_8px_hsl(24_100%_41%)]" />
        </div>
      </div>
    </div>
  );
}
