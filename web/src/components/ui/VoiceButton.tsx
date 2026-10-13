'use client';

import React from 'react';
import { clsx } from 'clsx';
import { Mic, Square, Loader2 } from 'lucide-react';

export type VoiceState = 'idle' | 'listening' | 'processing';

export interface VoiceButtonProps {
  state?: VoiceState;
  onClick?: () => void;
  label?: string;
  sublabel?: string;
  size?: 'md' | 'lg';
  className?: string;
}

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  state = 'idle',
  onClick,
  label = 'Tap to speak',
  sublabel,
  size = 'lg',
  className,
}) => {
  const isListening = state === 'listening';
  const isProcessing = state === 'processing';

  const buttonDimensions = size === 'lg' ? 'w-16 h-16 sm:w-20 sm:h-20' : 'w-12 h-12';
  const iconSize = size === 'lg' ? 'w-8 h-8 sm:w-10 sm:h-10' : 'w-6 h-6';

  return (
    <div className={clsx('flex flex-col items-center gap-2', className)}>
      <div className="relative flex items-center justify-center">
        {/* Pulsing concentric rings when active/listening */}
        {isListening && (
          <>
            <span className="absolute w-full h-full rounded-full bg-harvest-gold/40 animate-ping duration-1000" />
            <span className="absolute -inset-3 rounded-full bg-harvest-gold/20 animate-pulse duration-700" />
          </>
        )}

        <button
          type="button"
          onClick={onClick}
          disabled={isProcessing}
          aria-label={isListening ? 'Stop listening' : label}
          aria-pressed={isListening}
          className={clsx(
            'relative flex items-center justify-center rounded-full transition-all duration-200 select-none shadow-md active:scale-95 focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-2',
            buttonDimensions,
            isListening
              ? 'bg-danger text-white focus-visible:ring-danger shadow-danger/25'
              : 'bg-deep-leaf text-white hover:bg-[#18552e] focus-visible:ring-deep-leaf shadow-deep-leaf/25'
          )}
        >
          {isProcessing ? (
            <Loader2 className={clsx(iconSize, 'animate-spin')} />
          ) : isListening ? (
            <Square className={clsx(iconSize, 'fill-current')} />
          ) : (
            <Mic className={iconSize} />
          )}
        </button>
      </div>

      {(label || sublabel) && (
        <div className="text-center">
          <p
            className={clsx(
              'text-base font-bold',
              isListening ? 'text-danger animate-pulse' : 'text-ink'
            )}
          >
            {isListening ? 'Listening...' : label}
          </p>
          {sublabel && (
            <p className="text-xs text-muted max-w-[220px] mx-auto mt-0.5">
              {sublabel}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
