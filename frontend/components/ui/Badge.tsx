import React from 'react';

export type BadgeVariant = 'success' | 'warning' | 'error' | 'neutral' | 'info';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  pulse?: boolean;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; dot: string; border: string }> = {
  success: {
    bg: 'bg-emerald-950/60',
    text: 'text-emerald-400',
    dot: 'bg-emerald-500',
    border: 'border-emerald-800/40',
  },
  warning: {
    bg: 'bg-amber-950/60',
    text: 'text-amber-400',
    dot: 'bg-amber-500',
    border: 'border-amber-800/40',
  },
  error: {
    bg: 'bg-rose-950/60',
    text: 'text-rose-400',
    dot: 'bg-rose-500',
    border: 'border-rose-800/40',
  },
  info: {
    bg: 'bg-sky-950/60',
    text: 'text-sky-400',
    dot: 'bg-sky-500',
    border: 'border-sky-800/40',
  },
  neutral: {
    bg: 'bg-slate-900/60',
    text: 'text-slate-400',
    dot: 'bg-slate-500',
    border: 'border-slate-800/40',
  },
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', pulse = false }) => {
  const styles = variantStyles[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border tracking-wide uppercase ${styles.bg} ${styles.text} ${styles.border}`}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${styles.dot}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${styles.dot}`} />
      </span>
      {children}
    </span>
  );
};
