import { useState, useEffect, useRef } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: React.ReactNode;
  onLoad?: () => void;
}

export function LazyImage({ src, alt, className, placeholder, onLoad }: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [showPlaceholder, setShowPlaceholder] = useState(true);
  const intersectionRef = useRef<HTMLImageElement>(null);
  const hasIntersectionObserver = typeof window !== 'undefined' && 'IntersectionObserver' in window;

  useEffect(() => {
    if (!hasIntersectionObserver || !intersectionRef.current) {
      // Fallback: load immediately
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Image is visible, start loading
            const img = entry.target as HTMLImageElement;
            const srcToLoad = img.dataset.src || src;
            
            const image = new Image();
            image.onload = () => {
              img.src = srcToLoad;
            };
            image.onerror = () => {
              setShowPlaceholder(false);
              setIsLoaded(true);
            };
            image.src = srcToLoad;
            
            observer.unobserve(img);
          }
        });
      },
      { rootMargin: '200px' } // Start loading 200px before visible
    );

    observer.observe(intersectionRef.current);

    return () => {
      observer.disconnect();
    };
  }, [src, hasIntersectionObserver]);

  const handleLoad = () => {
    setIsLoaded(true);
    setShowPlaceholder(false);
    onLoad?.();
  };

  return (
    <div className="relative overflow-hidden rounded-lg bg-surface-2">
      {showPlaceholder && (
        <div className="animate-shimmer absolute inset-0 flex items-center justify-center">
          {placeholder || (
            <div className="h-full w-full skeleton-shimmer" />
          )}
        </div>
      )}
      <img
        ref={intersectionRef}
        src={isLoaded ? src : ''}
        data-src={src}
        alt={alt}
        className={`transition-opacity duration-300 ${className}`}
        style={{ opacity: isLoaded ? 1 : 0 }}
        onLoad={handleLoad}
        onError={() => {
          setShowPlaceholder(false);
          setIsLoaded(true);
        }}
        loading="lazy"
      />
    </div>
  );
}

// Hook for checking online/offline status
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof window !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

// Simple caching utility for offline support
export const cacheManager = {
  set: async (key: string, value: any): Promise<void> => {
    try {
      if ('indexedDB' in window) {
        const db = await openCacheDB();
        const transaction = db.transaction(['cache'], 'readwrite');
        const store = transaction.objectStore('cache');
        store.put(value, key);
      } else if (typeof localStorage !== 'undefined') {
        localStorage.setItem(`cache_${key}`, JSON.stringify(value));
      }
    } catch (e) {
      console.warn('Cache set failed:', e);
    }
  },

  get: async (key: string): Promise<any> => {
    try {
      if ('indexedDB' in window) {
        const db = await openCacheDB();
        return await new Promise((resolve) => {
          const request = db.transaction(['cache']).objectStore('cache').get(key);
          request.onsuccess = () => resolve(request.result);
        });
      } else if (typeof localStorage !== 'undefined') {
        const item = localStorage.getItem(`cache_${key}`);
        return item ? JSON.parse(item) : null;
      }
      return null;
    } catch (e) {
      console.warn('Cache get failed:', e);
      return null;
    }
  },

  clear: async (): Promise<void> => {
    try {
      if ('indexedDB' in window) {
        const db = await openCacheDB();
        const transaction = db.transaction(['cache'], 'readwrite');
        transaction.objectStore('cache').clear();
      } else if (typeof localStorage !== 'undefined') {
        Object.keys(localStorage).forEach((key) => {
          if (key.startsWith('cache_')) {
            localStorage.removeItem(key);
          }
        });
      }
    } catch (e) {
      console.warn('Cache clear failed:', e);
    }
  }
};

let cachedDB: IDBDatabase | null = null;

function openCacheDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (cachedDB) {
      resolve(cachedDB);
      return;
    }

    const request = indexedDB.open('mobile_cache', 1);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('cache')) {
        db.createObjectStore('cache');
      }
    };

    request.onsuccess = () => {
      cachedDB = request.result;
      resolve(cachedDB);
    };

    request.onerror = () => {
      reject(request.error);
    };
  });
}
