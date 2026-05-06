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
    if (id === 'any') {
      onClimateChange(climatePreferences.includes('any') ? [] : ['any']);
      return;
    }

    const selectedWithoutAny = climatePreferences.filter((c) => c !== 'any');

    if (climatePreferences.includes(id)) {
      onClimateChange(selectedWithoutAny.filter((c) => c !== id));
    } else if (selectedWithoutAny.length < 3) {
      onClimateChange([...selectedWithoutAny, id]);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Людность направлений</FieldLabel>
        <div className="mb-4 flex items-center gap-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
          <span className="text-[28px] leading-none transition-all duration-200">{CROWD_ICONS[crowd]}</span>
          <p className="text-[15px] font-semibold text-foreground">{CROWD_LABELS[crowd]}</p>
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
          <span className="text-[11px] text-muted-foreground">Нетуристические</span>
          <span className="text-[11px] text-muted-foreground">Оживлённые</span>
        </div>
      </div>

      <div>
        <FieldLabel>Предпочтения по климату</FieldLabel>
        <p className="mb-3 text-[13px] text-muted-foreground">До 3 вариантов</p>
        <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] gap-2">
          {CLIMATE_OPTIONS.map((opt) => {
            const isSelected = climatePreferences.includes(opt.id);
            const selectedSpecificCount = climatePreferences.filter((id) => id !== 'any').length;
            const isDisabled =
              opt.id !== 'any' &&
              !isSelected &&
              !climatePreferences.includes('any') &&
              selectedSpecificCount >= 3;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => toggleClimate(opt.id)}
                disabled={isDisabled}
                className={cn(
                  'flex min-w-0 items-center gap-2 rounded-2xl border px-2.5 py-3 text-left transition-all active:scale-[0.97]',
                  isSelected
                    ? 'border-primary/35 bg-primary/10 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                    : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))]',
                  isDisabled && 'opacity-40',
                )}
              >
                <span className="shrink-0 text-[20px] leading-none">{opt.emoji}</span>
                <span
                  className={cn(
                    'min-w-0 whitespace-nowrap text-[13px] font-semibold leading-tight',
                    opt.id === 'mediterranean' && 'text-[10.75px]',
                    isSelected ? 'text-primary' : 'text-foreground',
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
          className="min-h-[80px] resize-none rounded-[14px] border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-field))] px-3.5 py-3 text-[15px] placeholder:font-normal placeholder:italic placeholder:text-muted-foreground"
        />
      </div>
    </div>
  );
};
