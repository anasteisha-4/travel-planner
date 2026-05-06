import { groupPlacesByDate } from '@/entities/place';
import type { PlaceVisit } from '@/entities/place';
import {
  DndContext,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { SortableContext, arrayMove, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { MapPin } from 'lucide-react';

import { PlaceCard } from './PlaceCard';

const formatSectionDate = (dateStr: string): string => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    weekday: 'long',
  }).format(new Date(y, m - 1, d));
};

type PlaceListProps = {
  places: PlaceVisit[];
  onSelectPlace: (place: PlaceVisit) => void;
  onReorder: (date: string, placeIds: string[]) => void;
};

export const PlaceList = ({ places, onSelectPlace, onReorder }: PlaceListProps) => {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
  );

  if (places.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 pb-24 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-stone-100 dark:bg-[hsl(var(--surface-muted))]">
          <MapPin className="h-6 w-6 text-stone-400 dark:text-stone-500" />
        </div>
        <p className="text-[15px] font-semibold text-stone-500 dark:text-stone-400">Нет посещённых мест</p>
        <p className="text-[13px] text-stone-400 dark:text-stone-500">Добавьте первое место через карту</p>
      </div>
    );
  }

  const groups = groupPlacesByDate(places);
  const groupOffsets = groups.map((_, i) =>
    groups.slice(0, i).reduce((acc, g) => acc + g.places.length, 0),
  );

  return (
    <div className="flex-1 overflow-y-auto px-5 pb-28 pt-2">
      {groups.map((group, groupIdx) => {
        const groupStartIndex = groupOffsets[groupIdx];
        const ids = group.places.map((p) => p.id);

        const handleDragEnd = (event: DragEndEvent) => {
          const { active, over } = event;
          if (!over || active.id === over.id) return;
          const oldIdx = ids.indexOf(String(active.id));
          const newIdx = ids.indexOf(String(over.id));
          onReorder(group.date, arrayMove(ids, oldIdx, newIdx));
        };

        return (
          <div key={group.date} className="mb-5">
            <p className="mb-2.5 text-[11px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-500">
              {formatSectionDate(group.date)}
            </p>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={ids} strategy={verticalListSortingStrategy}>
                <div className="flex flex-col gap-2">
                  {group.places.map((place, i) => (
                    <PlaceCard
                      key={place.id}
                      place={place}
                      index={groupStartIndex + i}
                      onClick={() => onSelectPlace(place)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>
        );
      })}
    </div>
  );
};
