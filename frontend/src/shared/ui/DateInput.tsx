import { cn } from '@/shared/lib/utils';
import { Calendar as CalendarIcon } from 'lucide-react';
import * as React from 'react';

export type DateInputProps = Omit<React.ComponentProps<'input'>, 'type'> & {
  placeholder?: string;
};

const DateInput = React.forwardRef<HTMLInputElement, DateInputProps>(
  ({ className, value, onChange, placeholder, ...props }, ref) => {
    const formattedDate = React.useMemo(() => {
      if (!value) return '';
      try {
        const date = new Date(value.toString());
        if (isNaN(date.getTime())) return '';
        return new Intl.DateTimeFormat('ru-RU', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        }).format(date);
      } catch {
        return '';
      }
    }, [value]);

    return (
      <div className={cn('relative w-full', className)}>
        <div
          className={cn(
            'flex h-12 w-full items-center justify-between rounded-xl border border-input bg-transparent px-4 py-2 text-base shadow-sm ring-offset-background transition-colors placeholder:text-muted-foreground focus-within:ring-1 focus-within:ring-ring'
          )}
        >
          <span className={cn('block truncate', !value && 'text-muted-foreground')}>
            {formattedDate || placeholder}
          </span>
          <CalendarIcon className="h-4 w-4 text-muted-foreground" />
        </div>
        <input
          type="date"
          className="absolute inset-0 cursor-pointer opacity-0"
          value={value}
          onChange={onChange}
          ref={ref}
          {...props}
        />
      </div>
    );
  }
);

DateInput.displayName = 'DateInput';

export { DateInput };
