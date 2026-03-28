import type { PlaceVisit } from '@/entities/place';
import { cn } from '@/shared/lib/utils';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ChevronRight, GripVertical } from 'lucide-react';

type PlaceCardProps = {
  place: PlaceVisit;
  index: number;
  onClick: () => void;
};

export const PlaceCard = ({ place, index, onClick }: PlaceCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: place.id,
  });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn('flex min-w-0 items-center', isDragging && 'opacity-40')}
    >
      <button
        type="button"
        {...listeners}
        {...attributes}
        className="flex h-12 w-8 shrink-0 touch-none items-center justify-start text-stone-300 dark:text-stone-600"
        aria-label="Перетащить"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      <button
        type="button"
        onClick={onClick}
        className={cn(
          'flex min-w-0 flex-1 items-center gap-3.5 rounded-2xl px-2 py-3.5 text-left',
          'border border-white/20 bg-white/60 shadow-sm backdrop-blur-sm',
          'dark:border-stone-700/40 dark:bg-stone-900/60',
          'transition-transform active:scale-[0.98]'
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#2563EB] text-[11px] font-bold text-white shadow-sm">
          {index + 1}
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold text-stone-900 dark:text-white">
            {place.name}
          </p>
          {place.notes && (
            <p className="mt-0.5 truncate text-[12px] text-stone-400 dark:text-stone-500">
              {place.notes}
            </p>
          )}
        </div>

        <ChevronRight className="h-4 w-4 shrink-0 text-stone-300 dark:text-stone-600" />
      </button>
    </div>
  );
};
