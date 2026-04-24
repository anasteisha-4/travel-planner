// Re-export shared constants for onboarding-v2 feature usage
export {
  RISK_TOLERANCE_LABELS,
  VISA_OPTIONS,
  CLIMATE_OPTIONS,
  CROWD_LABELS,
  LANGUAGE_OPTIONS,
  DURATION_OPTIONS,
  TRAVEL_TYPES as VACATION_PREFERENCES_LIST,
} from '@/shared/config';

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

import type { VacationPreference } from '../model/types';

export type VacationPreferenceOption = {
  id: VacationPreference;
  label: string;
  icon: LucideIcon;
};

export const VACATION_PREFERENCES: VacationPreferenceOption[] = [
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

export type DurationOptionItem = {
  id: string;
  label: string;
  days: number;
};
