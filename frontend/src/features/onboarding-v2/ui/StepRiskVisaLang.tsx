import { cn } from '@/shared/lib/utils';
import { FieldLabel, PillChip, Slider } from '@/shared/ui';

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
  const risk = riskTolerance ?? 3;

  const selectedLanguage = languageComfort[0] ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Уровень приключений</FieldLabel>
        <div className="mb-4 flex items-center gap-3 rounded-2xl border border-stone-100 bg-stone-50 px-4 py-3">
          <span className="text-[28px] leading-none transition-all duration-200">{RISK_ICONS[risk]}</span>
          <p className="text-[15px] font-semibold text-stone-900">{RISK_TOLERANCE_LABELS[risk]}</p>
        </div>
        <div className="px-1">
          <Slider
            value={[risk]}
            onValueChange={([v]) => onRiskChange(v)}
            min={1}
            max={5}
            step={1}
            className="w-full"
          />
        </div>
        <div className="mt-2 flex justify-between px-1">
          <span className="text-[11px] text-stone-400">Безопасно</span>
          <span className="text-[11px] text-stone-400">Экзотика</span>
        </div>
      </div>

      <div>
        <FieldLabel>Визовые предпочтения</FieldLabel>
        <div className="flex flex-col gap-2">
          {VISA_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => onVisaChange(opt.id)}
              className={cn(
                'flex items-center justify-between rounded-2xl border px-4 py-3.5 text-left transition-all active:scale-[0.98]',
                visaTolerance === opt.id
                  ? 'border-blue-200 bg-blue-50 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                  : 'border-stone-200 bg-stone-50',
              )}
            >
              <div>
                <p
                  className={cn(
                    'text-[14px] font-semibold',
                    visaTolerance === opt.id ? 'text-blue-900' : 'text-stone-800',
                  )}
                >
                  {opt.label}
                </p>
                <p className="text-[12px] text-stone-400">{opt.description}</p>
              </div>
              <div
                className={cn(
                  'ml-3 h-5 w-5 shrink-0 rounded-full border-2 transition-colors',
                  visaTolerance === opt.id
                    ? 'border-blue-600 bg-blue-600'
                    : 'border-stone-300 bg-white',
                )}
              >
                {visaTolerance === opt.id && (
                  <div className="flex h-full items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-white" />
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <FieldLabel>Комфортные языки</FieldLabel>
        <div className="flex flex-wrap gap-2">
          {LANGUAGE_OPTIONS.map((opt) => (
            <PillChip
              key={opt.id}
              selected={selectedLanguage === opt.id}
              onClick={() => onLanguageChange([opt.id])}
            >
              {opt.label}
            </PillChip>
          ))}
        </div>
      </div>
    </div>
  );
};
