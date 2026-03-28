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
  RUB: { min: 0, max: 2000000, step: 10000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₽` },
  USD: { min: 0, max: 24000, step: 100, format: (v) => `$${v}` },
  EUR: { min: 0, max: 21000, step: 100, format: (v) => `€${v}` },
  GBP: { min: 0, max: 18000, step: 100, format: (v) => `£${v}` },
  TRY: { min: 0, max: 800000, step: 5000, format: (v) => `${(v / 1000).toFixed(0)}тыс ₺` },
  CNY: { min: 0, max: 160000, step: 1000, format: (v) => `¥${v}` },
};

import {
  Activity,
  Briefcase,
  ChefHat,
  Heart,
  Landmark,
  Leaf,
  Mountain,
  ShoppingBag,
  Sun,
  Users,
  type LucideIcon,
} from 'lucide-react';

export type TravelType = { id: string; label: string; icon: LucideIcon };

export const TRAVEL_TYPES: TravelType[] = [
  { id: 'beach', label: 'Пляжный', icon: Sun },
  { id: 'family', label: 'Семейный', icon: Users },
  { id: 'culture', label: 'Культура', icon: Landmark },
  { id: 'active', label: 'Активный', icon: Activity },
  { id: 'extreme', label: 'Экстрим', icon: Mountain },
  { id: 'shopping', label: 'Шопинг', icon: ShoppingBag },
  { id: 'gastro', label: 'Гастро', icon: ChefHat },
  { id: 'nature', label: 'Природа', icon: Leaf },
  { id: 'romantic', label: 'Романтика', icon: Heart },
  { id: 'business', label: 'Деловой', icon: Briefcase },
];

export const TRIP_DURATIONS = [
  { id: 'weekend', label: 'Выходные' },
  { id: 'week', label: 'Неделя' },
  { id: 'two_weeks', label: '2 недели' },
  { id: 'month', label: 'Месяц+' },
];
