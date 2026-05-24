import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { BUDGET_LIMITS } from '@/shared/config';
import { expenseApi } from '@/entities/expense';
import { sendEvent } from '@/shared/api';
import {
  HAPTIC_SINGLE_CONFIRM,
  HAPTIC_SINGLE_ERROR,
  useHapticFeedback,
} from '@/shared/lib/useHapticFeedback';
import { ensurePushNotifications } from '@/shared/lib';
import { invalidateProfileDependentQueries } from '@/shared/lib/profile-dependent-queries';

import { onboardingV2Api } from '../api/onboarding-v2.api';
import type {
  ClimatePref,
  DurationOption,
  LanguageOption,
  OnboardingStepData,
  RestLevel,
  UserProfileV2,
  VacationPreference,
  VisaTolerance,
} from './types';
import type { LikedDest } from '../ui/StepLikedDests'; // same feature slice — ok

type FieldErrors = Partial<Record<keyof OnboardingStepData, string>>;

type OnboardingState = {
  currentStep: number;
  vacationPreferencesRanked: VacationPreference[];
  preferredCurrency: string;
  budgetMin: number | null;
  budgetMax: number | null;
  restLevel: RestLevel | null;
  typicalDuration: DurationOption | null;
  originCityId: number | null;
  originCityName: string;
  originLat: number | null;
  originLng: number | null;
  citizenshipCode: string | null;
  likedDests: LikedDest[];
  riskTolerance: number | null;
  visaTolerance: VisaTolerance | null;
  languageComfort: LanguageOption[];
  crowdPreference: number | null;
  climatePreferences: ClimatePref[];
  freeTextNotes: string;
};

const DEFAULT_STATE: OnboardingState = {
  currentStep: 1,
  vacationPreferencesRanked: [],
  preferredCurrency: 'RUB',
  budgetMin: null,
  budgetMax: null,
  restLevel: null,
  typicalDuration: null,
  originCityId: null,
  originCityName: '',
  originLat: null,
  originLng: null,
  citizenshipCode: null,
  likedDests: [],
  riskTolerance: null,
  visaTolerance: null,
  languageComfort: [],
  crowdPreference: null,
  climatePreferences: [],
  freeTextNotes: '',
};

const profileToState = (profile: UserProfileV2): OnboardingState => ({
  currentStep: profile.onboarding_step > 0 ? Math.min(profile.onboarding_step, 6) : 1,
  vacationPreferencesRanked: (profile.vacation_preferences_ranked as VacationPreference[]) ?? [],
  preferredCurrency: profile.preferred_currency ?? 'RUB',
  budgetMin: profile.budget_min ?? null,
  budgetMax: profile.budget_max ?? null,
  restLevel: (profile.rest_level as RestLevel) ?? null,
  typicalDuration: (profile.typical_duration as DurationOption) ?? null,
  originCityId: profile.origin_city_id ?? null,
  originCityName: profile.origin_city_name ?? '',
  originLat: profile.origin_lat ?? null,
  originLng: profile.origin_lng ?? null,
  citizenshipCode: profile.citizenship_code ?? null,
  likedDests: (profile.liked_destination_ids ?? []).map((id, i) => ({
    id,
    name: profile.liked_destination_names?.[i] ?? id,
    country_code: '',
  })),
  riskTolerance: profile.risk_tolerance ?? null,
  visaTolerance: (profile.visa_tolerance as VisaTolerance) ?? null,
  languageComfort: (profile.language_comfort as LanguageOption[]) ?? [],
  crowdPreference: profile.crowd_preference ?? null,
  climatePreferences: (profile.climate_preferences as ClimatePref[]) ?? [],
  freeTextNotes: profile.free_text_notes ?? '',
});

const stateToStepPayload = (step: number, state: OnboardingState): OnboardingStepData => {
  switch (step) {
    case 1:
      return { vacation_preferences_ranked: state.vacationPreferencesRanked };
    case 2:
      return {
        preferred_currency: state.preferredCurrency,
        budget_min: state.budgetMin,
        budget_max: state.budgetMax,
        rest_level: state.restLevel ?? undefined,
        typical_duration: state.typicalDuration ?? undefined,
      };
    case 3:
      return {
        origin_city_id: state.originCityId ?? undefined,
        origin_city_name: state.originCityName || undefined,
        origin_lat: state.originLat ?? undefined,
        origin_lng: state.originLng ?? undefined,
        citizenship_code: state.citizenshipCode ?? undefined,
      };
    case 4:
      return {
        liked_destination_ids: state.likedDests.map((d) => d.id),
        liked_destination_names: state.likedDests.map((d) => d.name),
      };
    case 5:
      return {
        risk_tolerance: state.riskTolerance ?? undefined,
        visa_tolerance: state.visaTolerance ?? undefined,
        language_comfort: state.languageComfort,
      };
    case 6:
      return {
        crowd_preference: state.crowdPreference ?? undefined,
        climate_preferences: state.climatePreferences,
        free_text_notes: state.freeTextNotes || undefined,
      };
    default:
      return {};
  }
};

export const useOnboardingV2 = ({ onComplete }: { onComplete: () => void }) => {
  const qc = useQueryClient();
  const { play } = useHapticFeedback();

  const [state, setState] = useState<OnboardingState>(() => {
    const cached = qc.getQueryData<UserProfileV2>(['profile']);
    if (cached && !cached.onboarding_completed) return profileToState(cached);
    return DEFAULT_STATE;
  });
  const [errors, setErrors] = useState<FieldErrors>({});

  const { isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: onboardingV2Api.getProfile,
    staleTime: 1000 * 60 * 5,
  });

  const saveMutation = useMutation({
    mutationFn: ({ step, data }: { step: number; data: OnboardingStepData }) =>
      onboardingV2Api.saveOnboardingStep(step, data),
    onSuccess: (updated) => {
      qc.setQueryData(['profile'], updated);
      invalidateProfileDependentQueries(qc);
    },
    onError: () => {
      play(HAPTIC_SINGLE_ERROR);
    },
  });

  const completeMutation = useMutation({
    mutationFn: onboardingV2Api.completeOnboarding,
    onSuccess: (updated) => {
      play(HAPTIC_SINGLE_CONFIRM);
      qc.setQueryData(['profile'], updated);
      invalidateProfileDependentQueries(qc);
      void ensurePushNotifications().catch(() => false);
      onComplete();
    },
    onError: () => {
      play(HAPTIC_SINGLE_ERROR);
    },
  });

  const isSaving = saveMutation.isPending || completeMutation.isPending;

  const update = (patch: Partial<Omit<OnboardingState, 'currentStep'>>) => {
    setState((prev) => ({ ...prev, ...patch }));
    setErrors({});
  };

  const handleCurrencyChange = (newCurrency: string) => {
    const config = BUDGET_LIMITS[newCurrency] ?? BUDGET_LIMITS.RUB;
    const prevCurrency = state.preferredCurrency;
    const hasBudget = state.budgetMin !== null || state.budgetMax !== null;
    if (prevCurrency !== newCurrency) {
      sendEvent('currency_changed', {
        preferred_currency: newCurrency,
        previous_currency: prevCurrency,
        source: 'onboarding',
      });
    }

    if (!hasBudget || prevCurrency === newCurrency) {
      setState((prev) => ({
        ...prev,
        preferredCurrency: newCurrency,
        budgetMin: config.min,
        budgetMax: null,
      }));
      return;
    }

    setState((prev) => ({ ...prev, preferredCurrency: newCurrency }));

    qc.fetchQuery({
      queryKey: ['exchange-rates', prevCurrency],
      queryFn: () => expenseApi.getExchangeRates(prevCurrency),
      staleTime: 60 * 60 * 1000,
    }).then((rates) => {
      const rate = rates.rates[newCurrency];
      if (!rate) return;
      setState((s) => ({
        ...s,
        budgetMin: s.budgetMin !== null ? Math.round(s.budgetMin * rate) : null,
        budgetMax: s.budgetMax !== null ? Math.round(s.budgetMax * rate) : null,
      }));
    }).catch(() => {
      setState((s) => ({ ...s, budgetMin: config.min, budgetMax: null }));
    });
  };

  const goNext = async () => {
    const stepErrors: FieldErrors = {};
    if (Object.keys(stepErrors).length > 0) { setErrors(stepErrors); return; }

    saveMutation.mutate({ step: state.currentStep, data: stateToStepPayload(state.currentStep, state) });
    sendEvent('onboarding_step_completed', { step: state.currentStep });

    if (state.currentStep < 6) {
      setState((prev) => ({ ...prev, currentStep: prev.currentStep + 1 }));
    }
  };

  const goBack = () => {
    if (state.currentStep > 1) {
      setState((prev) => ({ ...prev, currentStep: prev.currentStep - 1 }));
      setErrors({});
    }
  };

  const handleComplete = async () => {
    await saveMutation.mutateAsync({ step: state.currentStep, data: stateToStepPayload(state.currentStep, state) });
    sendEvent('onboarding_step_completed', { step: state.currentStep });
    sendEvent('onboarding_completed');
    completeMutation.mutate();
  };

  const handleSaveAndExit = async () => {
    await saveMutation.mutateAsync({ step: state.currentStep, data: stateToStepPayload(state.currentStep, state) });
    sendEvent('onboarding_abandoned', { step: state.currentStep, source: 'save_and_exit' });
    play(HAPTIC_SINGLE_CONFIRM);
    onComplete();
  };

  return {
    currentStep: state.currentStep,
    vacationPreferencesRanked: state.vacationPreferencesRanked,
    preferredCurrency: state.preferredCurrency,
    budgetMin: state.budgetMin,
    budgetMax: state.budgetMax,
    restLevel: state.restLevel,
    typicalDuration: state.typicalDuration,
    originCityId: state.originCityId,
    originCityName: state.originCityName,
    originLat: state.originLat,
    originLng: state.originLng,
    citizenshipCode: state.citizenshipCode,
    likedDests: state.likedDests,
    riskTolerance: state.riskTolerance,
    visaTolerance: state.visaTolerance,
    languageComfort: state.languageComfort,
    crowdPreference: state.crowdPreference,
    climatePreferences: state.climatePreferences,
    freeTextNotes: state.freeTextNotes,
    isLoading,
    isSaving,
    errors,
    update,
    handleCurrencyChange,
    goNext,
    goBack,
    handleComplete,
    handleSaveAndExit,
  };
};
