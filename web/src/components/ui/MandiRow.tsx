import React from 'react';
import { clsx } from 'clsx';
import { MapPin, Calendar, ChevronRight } from 'lucide-react';

export interface MandiRowProps {
  mandiName: string;
  district: string;
  distanceKm?: number;
  modalPrice: number;
  priceUnit?: 'kg' | 'quintal';
  arrivalDate: string;
  arrivalQtyQuintal?: number;
  isNearest?: boolean;
  onClick?: () => void;
  className?: string;
  labels?: {
    distanceSuffix?: string;
    nearestBadge?: string;
    unitLabel?: string;
  };
}

export const MandiRow: React.FC<MandiRowProps> = ({
  mandiName,
  district,
  distanceKm,
  modalPrice,
  priceUnit = 'kg',
  arrivalDate,
  arrivalQtyQuintal,
  isNearest = false,
  onClick,
  className,
  labels = {
    distanceSuffix: 'km away',
    nearestBadge: 'Nearest',
    unitLabel: priceUnit === 'kg' ? '/kg' : '/qtl',
  },
}) => {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      className={clsx(
        'group flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-white border border-border rounded-xl transition-all duration-150 min-h-[56px]',
        onClick &&
          'cursor-pointer hover:border-deep-leaf/40 hover:bg-[#FAF9F0] focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf',
        className
      )}
    >
      {/* Left: Mandi Details */}
      <div className="flex items-start gap-3">
        <div className="p-2.5 rounded-xl bg-cream border border-border/80 text-deep-leaf flex-shrink-0 mt-0.5">
          <MapPin className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-heading text-lg font-bold text-ink leading-tight">
              {mandiName}
            </h4>
            {isNearest && (
              <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-harvest-gold text-ink">
                {labels.nearestBadge}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted mt-1 flex-wrap">
            <span>{district}</span>
            {distanceKm !== undefined && (
              <>
                <span aria-hidden="true">&bull;</span>
                <span className="font-medium text-ink">
                  {distanceKm} {labels.distanceSuffix}
                </span>
              </>
            )}
            {arrivalQtyQuintal !== undefined && (
              <>
                <span aria-hidden="true">&bull;</span>
                <span>{arrivalQtyQuintal} qtl</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Right: Price & Arrival date */}
      <div className="mt-3 sm:mt-0 flex items-center justify-between sm:justify-end gap-4 border-t sm:border-t-0 pt-2 sm:pt-0 border-border/50">
        <div className="text-left sm:text-right">
          <div className="flex items-baseline sm:justify-end gap-1">
            <span className="font-heading text-2xl font-extrabold text-deep-leaf">
              ₹{modalPrice.toLocaleString('en-IN')}
            </span>
            <span className="text-xs font-semibold text-muted">
              {labels.unitLabel}
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted mt-0.5">
            <Calendar className="w-3.5 h-3.5" />
            <span>{arrivalDate}</span>
          </div>
        </div>

        {onClick && (
          <div className="text-muted group-hover:text-deep-leaf transition-colors p-1">
            <ChevronRight className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  );
};
