import { cn } from '@/shared/lib/utils';

type StepIndicatorProps = {
  steps: number;
  current: number;
  barClassName?: string;
  className?: string;
};

export const StepIndicator = ({
  steps,
  current,
  barClassName = 'w-8',
  className,
}: StepIndicatorProps) => (
  <div className={cn('flex gap-1.5', className)}>
    {Array.from({ length: steps }, (_, i) => (
      <div
        key={i}
        className={cn(
          'h-1 rounded-full transition-colors',
          barClassName,
          i + 1 <= current ? 'bg-primary' : 'bg-stone-200 dark:bg-stone-700'
        )}
      />
    ))}
  </div>
);
