import { cn } from '@/shared/lib/utils';

export const FormError = ({ message, className }: { message?: string; className?: string }) => {
  return (
    <p
      className={cn(
        'min-h-[14px] text-[11px] font-medium leading-none',
        message ? 'text-red-500' : 'invisible',
        className
      )}
    >
      {message || 'x'}
    </p>
  );
};
