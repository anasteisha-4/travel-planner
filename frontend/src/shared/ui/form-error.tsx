import { cn } from '@/shared/lib/utils';

export const FormError = ({ message, className }: { message?: string; className?: string }) => {
  return (
    <p
      className={cn(
        'mt-2 min-h-[11px] text-[10px] font-medium leading-none',
        message ? 'text-red-500' : 'invisible',
        className
      )}
    >
      {message || 'x'}
    </p>
  );
};
