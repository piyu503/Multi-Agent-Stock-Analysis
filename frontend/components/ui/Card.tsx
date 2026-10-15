import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  action,
}) => {
  return (
    <div
      className={`relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70 backdrop-blur-md shadow-xl transition-all duration-300 hover:border-slate-700/80 ${className}`}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-emerald-500/5 pointer-events-none" />
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-slate-800/80 px-6 py-4">
          <div>
            {title && <h3 className="text-base font-semibold text-slate-100">{title}</h3>}
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-6 relative z-10">{children}</div>
    </div>
  );
};
