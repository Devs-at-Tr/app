import { useState, useEffect } from 'react';

/**
 * Custom hook to detect media query matches for responsive design
 * @param {string} query - Media query string (e.g., '(min-width: 768px)')
 * @returns {boolean} - Whether the media query matches
 * 
 * Usage:
 * const isMobile = useMediaQuery('(max-width: 767px)');
 * const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
 * const isDesktop = useMediaQuery('(min-width: 1024px)');
 */
export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    
    // Set initial value
    if (media.matches !== matches) {
      setMatches(media.matches);
    }

    // Create listener function
    const listener = (e) => setMatches(e.matches);
    
    // Add listener (modern API)
    if (media.addEventListener) {
      media.addEventListener('change', listener);
    } else {
      // Fallback for older browsers
      media.addListener(listener);
    }

    // Cleanup
    return () => {
      if (media.removeEventListener) {
        media.removeEventListener('change', listener);
      } else {
        media.removeListener(listener);
      }
    };
  }, [matches, query]);

  return matches;
};

// Predefined breakpoint hooks for convenience
export const useIsMobile = () => useMediaQuery('(max-width: 767px)');
export const useIsTablet = () => useMediaQuery('(min-width: 768px) and (max-width: 1024px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)');

export default useMediaQuery;
