import { cn } from '@/shared/lib/utils';

type SectionLabelProps = {
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
};

export const SectionLabel = ({ children, action, className }: SectionLabelProps) => (
  <div className={cn('flex items-center justify-between', className)}>
    <p className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
      {children}
    </p>
    {action}
  </div>
);
