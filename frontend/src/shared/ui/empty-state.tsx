type EmptyStateProps = {
  icon: React.ComponentType<{ className?: string }>;
  message: string;
  action?: React.ReactNode;
};

export const EmptyState = ({ icon: Icon, message, action }: EmptyStateProps) => (
  <div className="trip-info-card-muted flex flex-col items-center">
    <div className="flex flex-col items-center gap-1 py-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl">
        <Icon className="h-5 w-5 text-stone-400 dark:text-stone-500" />
      </div>
      <p className="text-center text-[14px] text-stone-400 dark:text-stone-500">{message}</p>
    </div>
    {action}
  </div>
);
