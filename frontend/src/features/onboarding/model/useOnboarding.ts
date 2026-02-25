import { useToast } from '@/shared/ui';
import { useState } from 'react';
import { onboardingApi } from '../api/onboarding.api';
import { BUDGET_LIMITS } from '../config/constants';

export const useOnboarding = ({ 
  onComplete, 
  onSkip 
}: { 
  onComplete: () => void; 
  onSkip: () => void; 
}) => {
  const [step, setStep] = useState(1);
  const [travelTypes, setTravelTypes] = useState<string[]>([]);
  const [destinations, setDestinations] = useState('');
  const [currency, setCurrency] = useState('RUB');
  const [budgetRange, setBudgetRange] = useState<[number, number]>([0, 100000]);
  const [tripDuration, setTripDuration] = useState<string | null>(null);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { toast } = useToast();

  const toggleTravelType = (id: string) => {
    setTravelTypes(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const handleCurrencyChange = (v: string) => {
    setCurrency(v);
    const config = BUDGET_LIMITS[v] || BUDGET_LIMITS.RUB;
    setBudgetRange([config.min, Math.round(config.max * 0.4)]);
  };

  const handleSkip = async () => {
    setIsLoading(true);
    try {
      await onboardingApi.updatePreferences({
        travel_types: [],
        favorite_destinations: null,
        currency: 'RUB',
        budget_min: null,
        budget_max: null,
        trip_duration: null,
        additional_info: null,
      });
      onSkip();
    } catch {
      onSkip();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      await onboardingApi.updatePreferences({
        travel_types: travelTypes,
        favorite_destinations: destinations || null,
        currency,
        budget_min: budgetRange[0] || null,
        budget_max: budgetRange[1] || null,
        trip_duration: tripDuration,
        additional_info: additionalInfo || null,
      });
      onComplete();
    } catch {
      toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось сохранить предпочтения' });
    } finally {
      setIsLoading(false);
    }
  };

  const budgetConfig = BUDGET_LIMITS[currency] || BUDGET_LIMITS.RUB;

  return {
    step,
    setStep,
    travelTypes,
    toggleTravelType,
    destinations,
    setDestinations,
    currency,
    handleCurrencyChange,
    budgetRange,
    setBudgetRange,
    tripDuration,
    setTripDuration,
    additionalInfo,
    setAdditionalInfo,
    isLoading,
    handleSkip,
    handleSave,
    budgetConfig,
  };
};
