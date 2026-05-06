import { markDiaryHintSeen } from '../model/diaryHint';
import { Button, Drawer, DrawerContent } from '@/shared/ui';
import { MapPin, Search } from 'lucide-react';

type DiaryHintSheetProps = {
  open: boolean;
  onClose: () => void;
};

export const DiaryHintSheet = ({ open, onClose }: DiaryHintSheetProps) => {
  const handleClose = () => {
    markDiaryHintSeen();
    onClose();
  };

  return (
    <Drawer open={open} onOpenChange={(v) => !v && handleClose()}>
      <DrawerContent className="bg-white pb-8 dark:bg-[hsl(var(--surface-elevated))]">
        <div className="px-5 pb-2 pt-1">
          <p className="mb-5 text-center text-[20px] font-extrabold text-stone-900 dark:text-white">
            Дневник поездки
          </p>

          <div className="mb-6 flex flex-col gap-3">
            <div className="flex items-start gap-3 rounded-2xl bg-stone-100 px-4 py-3.5 dark:bg-[hsl(var(--surface-muted))]">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/40">
                <Search className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-stone-900 dark:text-white">Поиск</p>
                <p className="mt-0.5 text-[13px] text-stone-500 dark:text-stone-400">
                  Введите название в строку поиска и выберите место из результатов
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-2xl bg-stone-100 px-4 py-3.5 dark:bg-[hsl(var(--surface-muted))]">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/40">
                <MapPin className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-stone-900 dark:text-white">Нажатие на карту</p>
                <p className="mt-0.5 text-[13px] text-stone-500 dark:text-stone-400">
                  Нажмите на любое место на карте, чтобы добавить его в дневник
                </p>
              </div>
            </div>
          </div>

          <Button
            className="h-[52px] w-full rounded-2xl text-base font-bold shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
            onClick={handleClose}
          >
            Понятно
          </Button>
        </div>
      </DrawerContent>
    </Drawer>
  );
};
