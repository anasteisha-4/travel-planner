import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { cn } from '@/shared/lib/utils';

type PillChipProps = {
  selected: boolean;
  onClick: () => void;
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  disabled?: boolean;
};

export const PillChip = ({ selected, onClick, icon: Icon, children, disabled }: PillChipProps) => {
  const { play } = useHapticFeedback();

  return (
    <button
      type="button"
      onClick={() => {
        if (!disabled) play('nudge');
        onClick();
      }}
      disabled={disabled}
      className={cn(
        'flex h-9 items-center gap-1.5 rounded-[10px] px-3.5 text-[14px] font-semibold transition-all active:scale-95',
        selected
          ? 'bg-primary text-white'
          : 'border border-stone-200 bg-stone-100 text-stone-600 dark:border-[hsl(var(--surface-border))] dark:bg-[hsl(var(--surface-muted))] dark:text-stone-300'
      )}
    >
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
      {children}
    </button>
  );
};
