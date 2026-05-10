import { useHapticFeedback } from '@/shared/lib/useHapticFeedback';

type ActionCardProps = {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  onClick: () => void;
  disabled?: boolean;
};

export const ActionCard = ({ icon: Icon, title, subtitle, onClick, disabled }: ActionCardProps) => {
  const { play } = useHapticFeedback();

  return (
    <button
      type="button"
      onClick={() => {
        if (!disabled) play('nudge');
        onClick();
      }}
      disabled={disabled}
      className="trip-info-card flex w-full items-center gap-4 text-left transition-all active:scale-[0.98] disabled:opacity-50"
    >
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] bg-primary/10 dark:bg-primary/20">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-bold text-stone-900 dark:text-white">{title}</p>
        {subtitle && (
          <p className="text-[13px] font-medium text-stone-400 dark:text-stone-500">{subtitle}</p>
        )}
      </div>
    </button>
  );
};
