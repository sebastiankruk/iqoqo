import * as React from "react";

/**
 * Hook to track media query state.
 * @param {string} query - The media query to track.
 * @returns {boolean} Whether the query matches.
 */
export function useMediaQuery(query: string) {
  const [value, setValue] = React.useState(false);

  React.useEffect(() => {
    /**
     * Handler for media query changes.
     * @param {MediaQueryListEvent} event - The change event.
     */
    function onChange(event: MediaQueryListEvent) {
      setValue(event.matches);
    }

    const result = window.matchMedia(query);
    result.addEventListener("change", onChange);
    setValue(result.matches);

    return () => result.removeEventListener("change", onChange);
  }, [query]);

  return value;
}
