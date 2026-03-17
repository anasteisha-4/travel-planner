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
        'h-[52px] w-full rounded-[14px] border border-stone-200 bg-stone-100 px-3.5 text-[15px] font-semibold text-stone-900 outline-none placeholder:font-normal placeholder:text-stone-400 focus:border-[1.5px] focus:border-primary dark:border-stone-700 dark:bg-stone-800 dark:text-white dark:placeholder:text-stone-500',
        error && 'border-red-300 bg-red-50 dark:border-red-800/50 dark:bg-red-900/20',
        className
      )}
      {...props}
    />
  )
);

AppInput.displayName = 'AppInput';
