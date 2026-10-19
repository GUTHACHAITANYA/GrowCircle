'use client';

import React from 'react';

export interface PriceSparklineProps {
  points?: number[];
  width?: number;
  height?: number;
  className?: string;
  showLabels?: boolean;
}

/**
 * 30-Day SVG Sparkline Component
 * Renders an inline miniature price trajectory with terminal point,
 * high/low metrics, and color-coded trendline (green for up/flat, red for down).
 */
export function PriceSparkline({
  points = [],
  width = 90,
  height = 26,
  className = '',
  showLabels = true,
}: PriceSparklineProps) {
  if (!points || points.length === 0) {
    return <span className="text-muted text-xs font-mono">&mdash;</span>;
  }

  if (points.length === 1) {
    return (
      <div className={`inline-flex items-center gap-1.5 ${className}`}>
        <span className="w-2 h-2 rounded-full bg-deep-leaf inline-block animate-pulse" />
        <span className="text-xs font-mono font-medium text-ink">₹{points[0].toFixed(1)}</span>
      </div>
    );
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const pad = 3;

  const coords = points.map((val, idx) => {
    const x = pad + (idx / Math.max(1, points.length - 1)) * (width - pad * 2);
    const y = height - pad - ((val - min) / range) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const isUp = points[points.length - 1] >= points[0];
  const strokeColor = isUp ? '#15803d' : '#b91c1c'; // emerald-700 or red-700
  const dPath = `M ${coords.join(' L ')}`;
  const lastCoord = coords[coords.length - 1].split(',');

  return (
    <div
      className={`inline-flex items-center gap-2 select-none ${className}`}
      title={`30-Day Auction History: Low ₹${min.toFixed(1)} &bull; High ₹${max.toFixed(1)}`}
    >
      <svg
        width={width}
        height={height}
        className="overflow-visible flex-shrink-0"
        role="img"
        aria-label="30-day price trend sparkline"
      >
        <path
          d={dPath}
          fill="none"
          stroke={strokeColor}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle
          cx={lastCoord[0]}
          cy={lastCoord[1]}
          r="2.5"
          fill={strokeColor}
          className="transition-all"
        />
      </svg>
      {showLabels && (
        <div className="flex flex-col text-[10px] font-mono leading-tight text-muted">
          <span className="text-emerald-800 font-semibold">H ₹{max.toFixed(0)}</span>
          <span className="text-ink">L ₹{min.toFixed(0)}</span>
        </div>
      )}
    </div>
  );
}
