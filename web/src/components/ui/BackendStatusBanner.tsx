'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw, WifiOff } from 'lucide-react';
import { checkBackendHealth, BackendHealthStatus, API_BASE } from '@/lib/api';

export const BackendStatusBanner: React.FC = () => {
  const [health, setHealth] = useState<BackendHealthStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const performCheck = async () => {
    setIsChecking(true);
    const result = await checkBackendHealth(3500);
    setHealth(result);
    setIsChecking(false);
  };

  useEffect(() => {
    performCheck();
    // Re-check periodically every 60 seconds
    const interval = setInterval(performCheck, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!health) return null;

  // If online and healthy, do not clutter UI unless dismissed
  if (health.isOnline && !dismissed) {
    return null;
  }

  // Backend is unreachable: show clear, friendly alert with action button
  if (!health.isOnline && !dismissed) {
    return (
      <aside
        role="alert"
        aria-label="Backend service connectivity alert"
        className="w-full bg-amber-500 text-ink px-4 py-2.5 border-b border-amber-600/30 text-xs sm:text-sm font-semibold flex items-center justify-between gap-3 shadow-xs"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <WifiOff className="w-4 h-4 text-ink flex-shrink-0" />
          <span className="truncate">
            <strong>Backend Unreachable:</strong> Unable to connect to GrowCircle API at{' '}
            <code className="bg-amber-600/20 px-1 py-0.5 rounded font-mono text-xs">{API_BASE}</code>.
            Live prices and OTP verification are currently simulated.
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={performCheck}
            disabled={isChecking}
            className="px-2.5 py-1 bg-ink text-white rounded-lg hover:bg-ink/80 transition-colors flex items-center gap-1.5 text-xs font-bold disabled:opacity-50"
            title="Retry connecting to backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin' : ''}`} />
            <span>{isChecking ? 'Checking...' : 'Retry'}</span>
          </button>
          <button
            onClick={() => setDismissed(true)}
            aria-label="Dismiss banner"
            className="p-1 hover:bg-amber-600/20 rounded text-ink"
          >
            ✕
          </button>
        </div>
      </aside>
    );
  }

  return null;
};
