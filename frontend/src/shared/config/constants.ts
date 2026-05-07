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
  RUB: { min: 0, max: 1000000, step: 10000, format: (v) => (v === 0 ? '0' : `${(v / 1000).toFixed(0)}тыс ₽`) },
  USD: { min: 0, max: 12000, step: 100, format: (v) => (v === 0 ? '0' : `$${v}`) },
  EUR: { min: 0, max: 11000, step: 100, format: (v) => (v === 0 ? '0' : `€${v}`) },
  GBP: { min: 0, max: 9000, step: 100, format: (v) => (v === 0 ? '0' : `£${v}`) },
  TRY: { min: 0, max: 400000, step: 5000, format: (v) => (v === 0 ? '0' : `${(v / 1000).toFixed(0)}тыс ₺`) },
  CNY: { min: 0, max: 80000, step: 1000, format: (v) => (v === 0 ? '0' : `¥${v}`) },
};

import {
  Activity,
  Briefcase,
  ChefHat,
  Heart,
  Landmark,
  Leaf,
  Moon,
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
  { id: 'nightlife', label: 'Ночная жизнь', icon: Moon },
  { id: 'shopping', label: 'Шопинг', icon: ShoppingBag },
  { id: 'gastro', label: 'Гастро', icon: ChefHat },
  { id: 'nature', label: 'Природа', icon: Leaf },
  { id: 'romantic', label: 'Романтика', icon: Heart },
  { id: 'business', label: 'Деловой', icon: Briefcase },
];

export const TRIP_DURATIONS = [
  { id: 'weekend', label: 'Выходные' },
  { id: 'short', label: 'Короткая (до недели)' },
  { id: 'standard', label: 'Стандартная (10 дней)' },
  { id: 'long', label: 'Длинная (3 недели)' },
  { id: 'extended', label: 'Долгая (месяц+)' },
];

export const RISK_TOLERANCE_LABELS: Record<number, string> = {
  1: 'Проверенные безопасные',
  2: 'В основном безопасные',
  3: 'Умеренный риск',
  4: 'Готов к приключениям',
  5: 'Экзотика и приключения',
};

export const VISA_OPTIONS = [
  { id: 'visa_free_only', label: 'Только безвиз', description: 'Страны без визы для моего паспорта' },
  { id: 'evisa_ok', label: 'Электронная виза', description: 'Безвиз + e-visa и визы по прилёту' },
  { id: 'any_visa', label: 'Любая виза', description: 'Готов оформить любую визу' },
] as const;

export const CLIMATE_OPTIONS = [
  { id: 'tropical_warm', label: 'Тропический', emoji: '🌴' },
  { id: 'mediterranean', label: 'Средиземноморский', emoji: '☀️' },
  { id: 'continental_mild', label: 'Умеренный', emoji: '🌿' },
  { id: 'cold_snow', label: 'Холодный / снег', emoji: '❄️' },
  { id: 'dry_desert', label: 'Сухой / пустыня', emoji: '🏜️' },
  { id: 'any', label: 'Любой климат', emoji: '🌍' },
] as const;

export const CROWD_LABELS: Record<number, string> = {
  1: 'Тихие нетуристические',
  2: 'Спокойные',
  3: 'Умеренные',
  4: 'Популярные',
  5: 'Оживлённые центры',
};

export const LANGUAGE_OPTIONS = [
  { id: 'ru', label: 'Русскоязычные' },
  { id: 'en', label: 'Англоязычные' },
  { id: 'any', label: 'Любые' },
] as const;

export const DURATION_OPTIONS = [
  { id: 'weekend', label: 'Выходные', days: 2 },
  { id: 'short', label: 'Короткая (до недели)', days: 5 },
  { id: 'standard', label: 'Стандартная (10 дней)', days: 10 },
  { id: 'long', label: 'Длинная (3 недели)', days: 21 },
  { id: 'extended', label: 'Долгая (месяц+)', days: 45 },
] as const;

export const REST_LEVEL_OPTIONS = [
  { id: 'economy', label: 'Экономно', description: 'Простое жильё и самые выгодные тарифы' },
  { id: 'standard', label: 'Стандарт', description: 'Обычные отели и средний тариф дороги' },
  { id: 'comfort', label: 'Комфорт', description: 'Лучше расположение, но без бизнес-класса' },
  { id: 'luxury', label: 'Люкс', description: 'Премиум-отели и бизнес-класс, если бюджет позволяет' },
] as const;
