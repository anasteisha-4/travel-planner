import { cn } from '@/shared/lib/utils';
import { HAPTIC_SINGLE_CONFIRM, HAPTIC_SINGLE_TAP, useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { FieldLabel, Slider } from '@/shared/ui';

import { LANGUAGE_OPTIONS, RISK_TOLERANCE_LABELS, VISA_OPTIONS } from '@/shared/config';
import type { LanguageOption, VisaTolerance } from '../model/types';

const RISK_ICONS: Record<number, string> = {
  1: '🛋️',
  2: '🏖️',
  3: '🗺️',
  4: '🧗',
  5: '🪂',
};

type Props = {
  riskTolerance: number | null;
  visaTolerance: VisaTolerance | null;
  languageComfort: LanguageOption[];
  onRiskChange: (v: number) => void;
  onVisaChange: (v: VisaTolerance) => void;
  onLanguageChange: (v: LanguageOption[]) => void;
};

export const StepRiskVisaLang = ({
  riskTolerance,
  visaTolerance,
  languageComfort,
  onRiskChange,
  onVisaChange,
  onLanguageChange,
}: Props) => {
  const { play } = useHapticFeedback();
  const risk = riskTolerance ?? 3;

  const selectedLanguage = languageComfort[0] ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Уровень приключений</FieldLabel>
        <div className="mb-4 flex items-center gap-3 rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
          <span className="text-[28px] leading-none transition-all duration-200">{RISK_ICONS[risk]}</span>
          <p className="text-[15px] font-semibold text-foreground">{RISK_TOLERANCE_LABELS[risk]}</p>
        </div>
        <div className="px-1">
          <Slider
            haptic={HAPTIC_SINGLE_TAP}
            value={[risk]}
            onValueChange={([v]) => onRiskChange(v)}
            min={1}
            max={5}
            step={1}
            className="w-full"
          />
        </div>
        <div className="mt-2 flex justify-between px-1">
          <span className="text-[11px] text-muted-foreground">Безопасно</span>
          <span className="text-[11px] text-muted-foreground">Экзотика</span>
        </div>
      </div>

      <div>
        <FieldLabel>Визовые предпочтения</FieldLabel>
        <div className="flex flex-col gap-2">
          {VISA_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => {
                play(visaTolerance === opt.id ? HAPTIC_SINGLE_TAP : HAPTIC_SINGLE_CONFIRM);
                onVisaChange(opt.id);
              }}
              className={cn(
                'flex items-center justify-between rounded-2xl border px-4 py-3.5 text-left transition-all active:scale-[0.98]',
                visaTolerance === opt.id
                  ? 'border-primary/35 bg-primary/10 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                  : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))]',
              )}
            >
              <div>
                <p
                  className={cn(
                    'text-[14px] font-semibold',
                    visaTolerance === opt.id ? 'text-primary' : 'text-foreground',
                  )}
                >
                  {opt.label}
                </p>
                <p className="text-[12px] text-muted-foreground">{opt.description}</p>
              </div>
              <div
                className={cn(
                  'ml-3 h-5 w-5 shrink-0 rounded-full border-2 transition-colors',
                  visaTolerance === opt.id
                    ? 'border-blue-600 bg-blue-600'
                    : 'border-stone-300 bg-[hsl(var(--surface))]',
                )}
              >
                {visaTolerance === opt.id && (
                  <div className="flex h-full items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-[hsl(var(--surface))]" />
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <FieldLabel>Комфортные языки</FieldLabel>
        <div className="grid grid-cols-3 gap-2">
          {LANGUAGE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => {
                play(selectedLanguage === opt.id ? HAPTIC_SINGLE_TAP : HAPTIC_SINGLE_CONFIRM);
                onLanguageChange([opt.id]);
              }}
              className={cn(
                'flex h-10 min-w-0 items-center justify-center rounded-[12px] px-2 text-center text-[clamp(11px,3.1vw,13px)] font-semibold leading-none transition-all active:scale-95',
                selectedLanguage === opt.id
                  ? 'bg-primary text-white'
                  : 'border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
