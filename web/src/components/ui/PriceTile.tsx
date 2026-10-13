import React from 'react';
import { clsx } from 'clsx';
import { ArrowUpRight, ArrowDownRight, Minus, AlertCircle, Clock } from 'lucide-react';
import { Card } from './Card';

export interface PriceTileProps {
  commodityName: string;
  variety?: string;
  modalPrice: number; // in rupees
  unit?: 'kg' | 'quintal';
  trend?: 'up' | 'down' | 'same';
  trendDiff?: number; // e.g. +3 or -2
  lastUpdated: string; // ISO date string or formatted time
  isStale?: boolean; // if >24 hours old
  mandiName?: string;
  className?: string;
  onClick?: () => void;
  // Localized strings
  labels?: {
    unitLabel?: string;
    modalPriceLabel?: string;
    lastUpdatedPrefix?: string;
    staleWarning?: string;
  };
}

export const PriceTile: React.FC<PriceTileProps> = ({
  commodityName,
  variety,
  modalPrice,
  unit = 'kg',
  trend = 'same',
  trendDiff,
  lastUpdated,
  isStale = false,
  mandiName,
  className,
  onClick,
  labels = {
    unitLabel: unit === 'kg' ? '/kg' : '/qtl',
    modalPriceLabel: 'Modal Price',
    lastUpdatedPrefix: 'Updated',
    staleWarning: 'Older than 24h',
  },
}) => {
  return (
    <Card
      isClickable={Boolean(onClick)}
      onClick={onClick}
      className={clsx('p-4 sm:p-5 flex flex-col justify-between', className)}
    >
      <div>
        {/* Top bar: Mandi name & stale warning */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          {mandiName && (
            <span className="text-xs font-semibold text-muted uppercase tracking-wider truncate">
              {mandiName}
            </span>
          )}
          {isStale && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-danger/10 text-danger border border-danger/20"
              title="Price data is older than 24 hours"
            >
              <AlertCircle className="w-3 h-3" />
              <span>{labels.staleWarning}</span>
            </span>
          )}
        </div>

        {/* Commodity & Variety */}
        <div className="mb-3">
          <h3 className="font-heading text-xl sm:text-2xl font-bold text-ink leading-tight">
            {commodityName}
          </h3>
          {variety && (
            <p className="text-sm text-muted font-medium mt-0.5">{variety}</p>
          )}
        </div>
      </div>

      {/* Price display & Trend */}
      <div className="pt-2 border-t border-border/60">
        <div className="flex items-baseline justify-between gap-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl sm:text-3xl font-extrabold text-deep-leaf font-heading">
              ₹{modalPrice.toLocaleString('en-IN')}
            </span>
            <span className="text-sm font-semibold text-muted">
              {labels.unitLabel}
            </span>
          </div>

          {/* Trend indicator */}
          <div className="flex items-center gap-1 font-semibold text-sm">
            {trend === 'up' && (
              <span className="inline-flex items-center text-deep-leaf bg-deep-leaf/10 px-2 py-1 rounded-lg">
                <ArrowUpRight className="w-4 h-4 mr-0.5" />
                {trendDiff ? `+₹${trendDiff}` : 'Up'}
              </span>
            )}
            {trend === 'down' && (
              <span className="inline-flex items-center text-danger bg-danger/10 px-2 py-1 rounded-lg">
                <ArrowDownRight className="w-4 h-4 mr-0.5" />
                {trendDiff ? `-₹${Math.abs(trendDiff)}` : 'Down'}
              </span>
            )}
            {trend === 'same' && (
              <span className="inline-flex items-center text-muted bg-black/5 px-2 py-1 rounded-lg">
                <Minus className="w-4 h-4 mr-0.5" />
                Stable
              </span>
            )}
          </div>
        </div>

        {/* Timestamp */}
        <div className="flex items-center gap-1.5 mt-2.5 text-xs text-muted">
          <Clock className="w-3.5 h-3.5 text-muted/80 flex-shrink-0" />
          <span>
            {labels.lastUpdatedPrefix}: {lastUpdated}
          </span>
        </div>
      </div>
    </Card>
  );
};
