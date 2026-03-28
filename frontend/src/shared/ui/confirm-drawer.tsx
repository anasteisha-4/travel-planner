import { AlertTriangle, Loader2, Trash2 } from 'lucide-react';
import { Button } from './button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from './drawer';

type ConfirmDrawerVariant = 'delete' | 'warning';

type ConfirmDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variant: ConfirmDrawerVariant;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
};

const VARIANT_STYLES = {
  delete: {
    iconWrapper:
      'border border-red-100/80 bg-red-50/80 dark:border-red-900/60 dark:bg-red-900/20',
    icon: <Trash2 className="h-6 w-6 text-red-500" />,
    confirmButton: (
      loading: boolean,
      label: string,
      onClick: () => void,
      disabled: boolean,
    ) => (
      <Button
        variant="destructive"
        className="h-[52px] w-full rounded-2xl text-base font-bold"
        onClick={onClick}
        disabled={disabled}
      >
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {label}
      </Button>
    ),
  },
  warning: {
    iconWrapper:
      'border border-amber-200/80 bg-amber-50/80 dark:border-amber-800/60 dark:bg-amber-900/20',
    icon: <AlertTriangle className="h-6 w-6 text-amber-500" />,
    confirmButton: (
      loading: boolean,
      label: string,
      onClick: () => void,
      disabled: boolean,
    ) => (
      <button
        type="button"
        className="flex h-[52px] w-full items-center justify-center rounded-2xl border border-amber-300 bg-transparent text-base font-bold text-amber-700 disabled:opacity-50 dark:border-amber-700 dark:text-amber-400"
        onClick={onClick}
        disabled={disabled}
      >
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {label}
      </button>
    ),
  },
} satisfies Record<
  ConfirmDrawerVariant,
  {
    iconWrapper: string;
    icon: React.ReactNode;
    confirmButton: (
      loading: boolean,
      label: string,
      onClick: () => void,
      disabled: boolean,
    ) => React.ReactNode;
  }
>;

export const ConfirmDrawer = ({
  open,
  onOpenChange,
  variant,
  title,
  description,
  confirmLabel,
  cancelLabel = 'Отмена',
  onConfirm,
  loading = false,
}: ConfirmDrawerProps) => {
  const styles = VARIANT_STYLES[variant];

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="bg-white px-5 pb-10 dark:bg-stone-950">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className={`confirmation-sheet-icon mb-4 ${styles.iconWrapper}`}>
            {styles.icon}
          </div>
          <DrawerHeader>
            <DrawerTitle className="text-[22px] font-extrabold text-stone-900 dark:text-white">
              {title}
            </DrawerTitle>
          </DrawerHeader>
          <p className="mt-1.5 text-sm text-stone-400 dark:text-stone-500">{description}</p>
        </div>
        <div className="flex flex-col gap-3">
          {styles.confirmButton(loading, confirmLabel, onConfirm, loading)}
          <Button
            variant="outline"
            className="h-[52px] w-full rounded-2xl border-stone-200 bg-stone-100 text-base font-bold text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
        </div>
      </DrawerContent>
    </Drawer>
  );
};
