import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';

import { cn } from '@/shared/lib/utils';
import { FieldLabel } from '@/shared/ui';

import { VACATION_PREFERENCES } from '../config/constants';
import type { VacationPreference } from '../model/types';

type SortableItemProps = {
  id: VacationPreference;
  rank: number;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onRemove: () => void;
};

const SortableItem = ({ id, rank, label, icon: Icon, onRemove }: SortableItemProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'flex items-center gap-3 rounded-2xl border bg-white px-3 py-3 shadow-sm transition-shadow',
        isDragging
          ? 'z-50 border-blue-300 shadow-[0_8px_24px_rgba(37,99,235,0.18)]'
          : 'border-stone-200',
      )}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        className="touch-none cursor-grab active:cursor-grabbing p-1 -ml-1"
        aria-label="Перетащить"
      >
        <GripVertical className="h-4 w-4 text-stone-300" />
      </button>
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[11px] font-bold text-white">
        {rank}
      </span>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-50">
        <Icon className="h-4 w-4 text-blue-600" />
      </div>
      <span className="flex-1 text-[14px] font-semibold text-stone-900">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-100 text-stone-400 transition-colors hover:bg-red-50 hover:text-red-500"
        aria-label="Убрать"
      >
        ×
      </button>
    </div>
  );
};

type Props = {
  selected: VacationPreference[];
  onChange: (value: VacationPreference[]) => void;
  error?: string;
};

export const StepVacationPrefs = ({ selected, onChange, error }: Props) => {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
  );

  const toggle = (id: VacationPreference) => {
    if (selected.includes(id)) {
      onChange(selected.filter((x) => x !== id));
    } else if (selected.length < 5) {
      onChange([...selected, id]);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIdx = selected.indexOf(active.id as VacationPreference);
      const newIdx = selected.indexOf(over.id as VacationPreference);
      onChange(arrayMove(selected, oldIdx, newIdx));
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div>
        <FieldLabel>Виды отдыха</FieldLabel>
        <p className="mb-4 text-[13px] text-stone-400">
          Выберите до 5 — порядок важен, перетащите для изменения приоритета
        </p>
        <div className="grid grid-cols-2 gap-2">
          {VACATION_PREFERENCES.map((pref) => {
            const isSelected = selected.includes(pref.id);
            const Icon = pref.icon;
            return (
              <button
                key={pref.id}
                type="button"
                onClick={() => toggle(pref.id)}
                disabled={!isSelected && selected.length >= 5}
                className={cn(
                  'flex items-center gap-2.5 rounded-2xl border px-3.5 py-3 text-left transition-all active:scale-[0.97]',
                  isSelected
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-stone-200 bg-stone-50',
                  !isSelected && selected.length >= 5 && 'opacity-35',
                )}
              >
                <div className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl',
                  isSelected ? 'bg-blue-600' : 'bg-stone-200',
                )}>
                  <Icon className={cn('h-4 w-4', isSelected ? 'text-white' : 'text-stone-500')} />
                </div>
                <span className={cn(
                  'text-[13px] font-semibold leading-tight',
                  isSelected ? 'text-blue-900' : 'text-stone-700',
                )}>
                  {pref.label}
                </span>
              </button>
            );
          })}
        </div>
        {error && <p className="mt-2 text-[13px] text-red-500">{error}</p>}
      </div>

      {selected.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-stone-400">
            Приоритет — перетащите для изменения порядка
          </p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={selected} strategy={verticalListSortingStrategy}>
              <div className="flex flex-col gap-2">
                {selected.map((id, idx) => {
                  const pref = VACATION_PREFERENCES.find((p) => p.id === id)!;
                  return (
                    <SortableItem
                      key={id}
                      id={id}
                      rank={idx + 1}
                      label={pref.label}
                      icon={pref.icon}
                      onRemove={() => onChange(selected.filter((x) => x !== id))}
                    />
                  );
                })}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      )}
    </div>
  );
};
