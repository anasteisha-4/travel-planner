type BudgetSliderConfig = {
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
};

const FINITE_SLIDER_MAX = 99;
export const UNLIMITED_BUDGET_SLIDER_VALUE = 100;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const roundToStep = (value: number, step: number) => Math.round(value / step) * step;

export const budgetAmountToSliderValue = (amount: number | null | undefined, config: BudgetSliderConfig) => {
  if (amount === null || amount === undefined) return UNLIMITED_BUDGET_SLIDER_VALUE;
  if (amount <= config.min) return 0;

  const normalized = clamp(amount / config.max, 0, 1);
  return Math.round(Math.sqrt(normalized) * FINITE_SLIDER_MAX);
};

export const budgetSliderValueToAmount = (value: number, config: BudgetSliderConfig) => {
  if (value >= UNLIMITED_BUDGET_SLIDER_VALUE) return null;
  if (value <= 0) return config.min;

  const normalized = value / FINITE_SLIDER_MAX;
  const amount = config.max * normalized * normalized;
  return clamp(roundToStep(amount, config.step), config.min, config.max);
};

export const formatBudgetLimit = (amount: number | null | undefined, config: BudgetSliderConfig) =>
  amount === null || amount === undefined ? 'Без лимита' : config.format(amount);
