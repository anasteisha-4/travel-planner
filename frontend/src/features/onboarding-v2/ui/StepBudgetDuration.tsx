import { BUDGET_LIMITS, CURRENCIES } from '@/shared/config';
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
  onCurrencyChange: (v: string) => void;
  onBudgetChange: (min: number, max: number) => void;
};

export const StepBudgetDuration = ({
  currency,
  budgetMin,
  budgetMax,
  onCurrencyChange,
  onBudgetChange,
}: Props) => {
  const cfg = BUDGET_LIMITS[currency] ?? BUDGET_LIMITS.RUB;
  const min = budgetMin ?? cfg.min;
  const max = budgetMax ?? Math.round(cfg.max * 0.3);

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
            <p className="text-[20px] font-bold text-foreground">{cfg.format(min)}</p>
          </div>
          <div className="mx-4 h-px flex-1 bg-[hsl(var(--surface-field))]" />
          <div className="text-center">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">до</p>
            <p className="text-[20px] font-bold text-foreground">{cfg.format(max)}</p>
          </div>
        </div>
        <div className="px-1">
          <Slider
            value={[min, max]}
            onValueChange={([a, b]) => onBudgetChange(a, b)}
            min={cfg.min}
            max={cfg.max}
            step={cfg.step}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
};
