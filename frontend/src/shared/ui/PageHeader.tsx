import { cn } from '@/shared/lib/utils';
import type { ReactNode } from 'react';

type PageHeaderProps = {
  children: ReactNode;
  className?: string;
};

export const PageHeader = ({ children, className }: PageHeaderProps) => (
  <div
    className={cn(
      'sticky top-0 z-20 -mx-4 mb-2 flex items-center bg-background/70 px-4 pb-3 pt-[calc(env(safe-area-inset-top)+1rem)] backdrop-blur-xl',
      className
    )}
  >
    {children}
  </div>
);
