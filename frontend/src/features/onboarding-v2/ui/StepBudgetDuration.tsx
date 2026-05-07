import type { RestLevel } from '@/entities/user';
import { BUDGET_LIMITS, CURRENCIES, REST_LEVEL_OPTIONS } from '@/shared/config';
import {
  budgetAmountToSliderValue,
  budgetSliderValueToAmount,
  formatBudgetLimit,
  UNLIMITED_BUDGET_SLIDER_VALUE,
} from '@/shared/lib';
import { cn } from '@/shared/lib/utils';
import {
  FieldLabel,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
} from '@/shared/ui';

type Props = {
  currency: string;
  budgetMin: number | null;
  budgetMax: number | null;
  restLevel: RestLevel | null;
  onCurrencyChange: (v: string) => void;
  onBudgetChange: (min: number | null, max: number | null) => void;
  onRestLevelChange: (v: RestLevel) => void;
};

export const StepBudgetDuration = ({
  currency,
  budgetMin,
  budgetMax,
  restLevel,
  onCurrencyChange,
  onBudgetChange,
  onRestLevelChange,
}: Props) => {
  const cfg = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;
  const min = budgetMin ?? cfg.min;
  const max = budgetMax ?? null;
  const sliderValue = [
    Math.min(budgetAmountToSliderValue(min, cfg), UNLIMITED_BUDGET_SLIDER_VALUE - 1),
    budgetAmountToSliderValue(max, cfg),
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <FieldLabel>Валюта бюджета</FieldLabel>
        <Select value={currency} onValueChange={onCurrencyChange}>
          <SelectTrigger className="h-[52px] w-full rounded-[14px] border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-field))] text-[15px] font-semibold">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CURRENCIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <FieldLabel>Бюджет поездки</FieldLabel>
        <div className="mb-4 flex items-center justify-between rounded-2xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-4 py-3">
          <div className="text-center">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">от</p>
            <p className="text-[20px] font-bold text-foreground">{formatBudgetLimit(min, cfg)}</p>
          </div>
          <div className="mx-4 h-px flex-1 bg-[hsl(var(--surface-field))]" />
          <div className="text-center">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">до</p>
            <p className="text-[20px] font-bold text-foreground">{formatBudgetLimit(max, cfg)}</p>
          </div>
        </div>
        <div className="px-1">
          <Slider
            value={sliderValue}
            onValueChange={([a, b]) => {
              const nextMin = budgetSliderValueToAmount(Math.min(a, UNLIMITED_BUDGET_SLIDER_VALUE - 1), cfg);
              const nextMax = budgetSliderValueToAmount(b, cfg);
              onBudgetChange(nextMin, nextMax);
            }}
            min={0}
            max={UNLIMITED_BUDGET_SLIDER_VALUE}
            step={1}
            className="w-full"
          />
          <div className="mt-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.04em] text-muted-foreground">
            <span>0</span>
            <span>Без лимита</span>
          </div>
        </div>
      </div>

      <div>
        <FieldLabel>Уровень отдыха</FieldLabel>
        <div className="grid grid-cols-2 gap-2">
          {REST_LEVEL_OPTIONS.map((option) => {
            const selected = restLevel === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => onRestLevelChange(option.id)}
                className={cn(
                  'min-h-[78px] rounded-2xl border px-3 py-2.5 text-left transition-colors',
                  selected
                    ? 'border-primary bg-primary/10 text-foreground'
                    : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] text-foreground active:bg-[hsl(var(--surface-field))]'
                )}
              >
                <span className="block text-[14px] font-extrabold">{option.label}</span>
                <span className="mt-1 block text-[11px] font-semibold leading-snug text-muted-foreground">
                  {option.description}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
