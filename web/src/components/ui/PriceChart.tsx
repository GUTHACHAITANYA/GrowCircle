'use client';

import React, { useState } from 'react';
import { clsx } from 'clsx';
import { TrendingUp } from 'lucide-react';

export interface ChartDataPoint {
  date: string;
  modalPrice: number; // in ₹/kg
  modalPriceQuintal?: number;
  arrivalTonnes?: number;
}

export interface PriceChartProps {
  data: ChartDataPoint[];
  commodityName?: string;
  mandiName?: string;
  className?: string;
}

export const PriceChart: React.FC<PriceChartProps> = ({
  data,
  commodityName = 'Banana',
  mandiName = 'Guntur Mandi',
  className,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<ChartDataPoint | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center bg-cream/40 rounded-2xl border border-border text-muted text-sm">
        No historical price data available.
      </div>
    );
  }

  // Dimensions
  const width = 800;
  const height = 300;
  const paddingX = 40;
  const paddingY = 40;

  const prices = data.map((d) => d.modalPrice);
  const minPrice = Math.min(...prices) * 0.95;
  const maxPrice = Math.max(...prices) * 1.05;
  const priceRange = maxPrice - minPrice || 1;

  // Compute SVG coordinates
  const points = data.map((d, index) => {
    const x = paddingX + (index / (data.length - 1)) * (width - paddingX * 2);
    const y = height - paddingY - ((d.modalPrice - minPrice) / priceRange) * (height - paddingY * 2);
    return { x, y, data: d };
  });

  const pathD = points.reduce((acc, p, idx) => {
    return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  return (
    <div className={clsx('bg-white p-6 rounded-2xl border border-border shadow-sm flex flex-col', className)}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-deep-leaf" />
            <h3 className="font-heading text-lg font-bold text-ink">
              30-Day Modal Price Trend ({commodityName})
            </h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Historical Agmarknet daily rates &bull; {mandiName}
          </p>
        </div>

        {hoveredPoint ? (
          <div className="px-3 py-1.5 rounded-xl bg-cream border border-border text-xs flex items-center gap-2">
            <span className="font-medium text-muted">{hoveredPoint.date}:</span>
            <span className="font-bold text-deep-leaf text-sm font-heading">
              ₹{hoveredPoint.modalPrice.toFixed(2)}/kg
            </span>
          </div>
        ) : (
          <div className="text-xs text-muted font-medium">
            Range: ₹{minPrice.toFixed(0)} - ₹{maxPrice.toFixed(0)}/kg
          </div>
        )}
      </div>

      {/* Responsive SVG Chart */}
      <div className="relative w-full aspect-[8/3] max-h-72">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
        >
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1F6B3A" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#1F6B3A" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const y = height - paddingY - pct * (height - paddingY * 2);
            const val = minPrice + pct * priceRange;
            return (
              <g key={pct}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#E3E0D2"
                  strokeDasharray="4 4"
                />
                <text
                  x={paddingX - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="text-[10px] fill-muted font-sans"
                >
                  ₹{val.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Gradient area */}
          <path d={areaD} fill="url(#chartGradient)" />

          {/* Line stroke */}
          <path
            d={pathD}
            fill="none"
            stroke="#1F6B3A"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Data Points */}
          {points.map((p, idx) => (
            <circle
              key={idx}
              cx={p.x}
              cy={p.y}
              r={hoveredPoint?.date === p.data.date ? 6 : 3.5}
              fill={hoveredPoint?.date === p.data.date ? "#F6C343" : "#1F6B3A"}
              stroke="#FFFFFF"
              strokeWidth="2"
              className="cursor-pointer transition-all duration-150"
              onMouseEnter={() => setHoveredPoint(p.data)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
        </svg>
      </div>

      <div className="flex justify-between items-center text-[11px] text-muted font-medium mt-3 px-2 border-t border-border/50 pt-2">
        <span>{data[0]?.date}</span>
        <span>Past 30 Days</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
};
