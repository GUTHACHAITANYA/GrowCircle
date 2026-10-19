'use client';

import { useEffect } from 'react';

export function ServiceWorkerRegister() {
  useEffect(() => {
    if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/sw.js')
          .then((reg) => {
            console.log('GrowCircle PWA ServiceWorker active, scope:', reg.scope);
          })
          .catch((err) => {
            console.warn('GrowCircle PWA ServiceWorker registration error:', err);
          });
      });
    }
  }, []);

  return null;
}
