export const CURRENCIES = [
  { value: 'RUB', label: '₽ Рубль' },
  { value: 'USD', label: '$ Доллар' },
  { value: 'EUR', label: '€ Евро' },
  { value: 'GBP', label: '£ Фунт' },
  { value: 'TRY', label: '₺ Лира' },
  { value: 'CNY', label: '¥ Юань' },
];

export const BUDGET_LIMITS: Record<
  string,
  { min: number; max: number; step: number; format: (v: number) => string }
> = {
  RUB: { min: 0, max: 1000000, step: 10000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₽` },
  USD: { min: 0, max: 10000, step: 100, format: (v) => `$${v}` },
  EUR: { min: 0, max: 10000, step: 100, format: (v) => `€${v}` },
  GBP: { min: 0, max: 8000, step: 100, format: (v) => `£${v}` },
  TRY: { min: 0, max: 350000, step: 5000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₺` },
  CNY: { min: 0, max: 75000, step: 1000, format: (v) => `¥${v}` },
};

export const TRAVEL_TYPES = [
  { id: 'beach', label: '🏖️ Пляжный' },
  { id: 'family', label: '👨‍👩‍👧 Семейный' },
  { id: 'culture', label: '🏛️ Культура и история' },
  { id: 'active', label: '🚴 Активный' },
  { id: 'extreme', label: '🧗 Экстремальный' },
  { id: 'shopping', label: '🛍️ Шопинг' },
  { id: 'gastro', label: '🍽️ Гастрономический' },
  { id: 'nature', label: '🌲 Природа и эко' },
  { id: 'romantic', label: '💕 Романтический' },
  { id: 'business', label: '💼 Деловой' },
];

export const TRIP_DURATIONS = [
  { id: 'weekend', label: 'Выходные' },
  { id: 'week', label: 'Неделя' },
  { id: 'two_weeks', label: '2 недели' },
  { id: 'month', label: 'Месяц+' },
];
