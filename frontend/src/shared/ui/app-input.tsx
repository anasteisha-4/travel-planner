import { cn } from '@/shared/lib/utils';
import { forwardRef } from 'react';

type AppInputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  error?: boolean;
};

export const AppInput = forwardRef<HTMLInputElement, AppInputProps>(
  ({ error, className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'h-[52px] w-full rounded-[14px] app-field px-3.5 text-[15px] font-semibold text-foreground outline-none placeholder:font-normal placeholder:text-muted-foreground focus:border-[1.5px] focus:border-primary',
        error && 'border-red-300 bg-red-50 dark:border-red-500/50 dark:bg-red-950/30',
        className
      )}
      {...props}
    />
  )
);

AppInput.displayName = 'AppInput';
