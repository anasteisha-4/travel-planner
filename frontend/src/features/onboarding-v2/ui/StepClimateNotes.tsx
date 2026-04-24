import { cn } from '@/shared/lib/utils';
import { FieldLabel, Slider, Textarea } from '@/shared/ui';

import { CLIMATE_OPTIONS, CROWD_LABELS } from '@/shared/config';
import type { ClimatePref } from '../model/types';

const CROWD_ICONS: Record<number, string> = {
  1: '🏕️',
  2: '🌄',
  3: '🏘️',
  4: '🏙️',
  5: '🎡',
};

type Props = {
  crowdPreference: number | null;
  climatePreferences: ClimatePref[];
  freeTextNotes: string;
  onCrowdChange: (v: number) => void;
  onClimateChange: (v: ClimatePref[]) => void;
  onNotesChange: (v: string) => void;
};

export const StepClimateNotes = ({
  crowdPreference,
  climatePreferences,
  freeTextNotes,
  onCrowdChange,
  onClimateChange,
  onNotesChange,
}: Props) => {
  const crowd = crowdPreference ?? 3;

  const toggleClimate = (id: ClimatePref) => {
    if (climatePreferences.includes(id)) {
      onClimateChange(climatePreferences.filter((c) => c !== id));
    } else if (climatePreferences.length < 3) {
      onClimateChange([...climatePreferences, id]);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Людность направлений</FieldLabel>
        <div className="mb-4 flex items-center gap-3 rounded-2xl border border-stone-100 bg-stone-50 px-4 py-3">
          <span className="text-[28px] leading-none transition-all duration-200">{CROWD_ICONS[crowd]}</span>
          <p className="text-[15px] font-semibold text-stone-900">{CROWD_LABELS[crowd]}</p>
        </div>
        <div className="px-1">
          <Slider
            value={[crowd]}
            onValueChange={([v]) => onCrowdChange(v)}
            min={1}
            max={5}
            step={1}
            className="w-full"
          />
        </div>
        <div className="mt-2 flex justify-between px-1">
          <span className="text-[11px] text-stone-400">Нетуристические</span>
          <span className="text-[11px] text-stone-400">Оживлённые</span>
        </div>
      </div>

      <div>
        <FieldLabel>Предпочтения по климату</FieldLabel>
        <p className="mb-3 text-[13px] text-stone-400">До 3 вариантов</p>
        <div className="grid grid-cols-2 gap-2">
          {CLIMATE_OPTIONS.map((opt) => {
            const isSelected = climatePreferences.includes(opt.id);
            const isDisabled = !isSelected && climatePreferences.length >= 3;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => toggleClimate(opt.id)}
                disabled={isDisabled}
                className={cn(
                  'flex items-center gap-3 rounded-2xl border px-3.5 py-3 text-left transition-all active:scale-[0.97]',
                  isSelected
                    ? 'border-blue-200 bg-blue-50 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                    : 'border-stone-200 bg-stone-50',
                  isDisabled && 'opacity-40',
                )}
              >
                <span className="text-[20px] leading-none">{opt.emoji}</span>
                <span
                  className={cn(
                    'text-[13px] font-semibold leading-tight',
                    isSelected ? 'text-blue-900' : 'text-stone-700',
                  )}
                >
                  {opt.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <FieldLabel>Дополнительные пожелания</FieldLabel>
        <Textarea
          placeholder="Аллергии, ограничения, что угодно..."
          value={freeTextNotes}
          onChange={(e) => onNotesChange(e.target.value)}
          className="min-h-[80px] resize-none rounded-[14px] border-stone-200 bg-stone-100 px-3.5 py-3 text-[15px] placeholder:font-normal placeholder:italic placeholder:text-stone-400"
        />
      </div>
    </div>
  );
};
