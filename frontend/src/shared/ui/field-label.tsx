import { cn } from '@/shared/lib/utils';

export const FieldLabel = ({
  children,
  className,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) => (
  <label
    className={cn(
      'mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500',
      className
    )}
    {...props}
  >
    {children}
  </label>
);
