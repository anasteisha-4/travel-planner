import type { Trip } from '@/entities/trip';
import { profileApi } from '@/features/profile';
import { TripForm, type TripFormInitialValues } from '@/features/trips';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft } from 'lucide-react';
import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const getParamNumber = (value: string | null): number | undefined => {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
};

export const TripCreatePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const hasRecommendationPrefill = searchParams.has('destination');
  const { data: profile, isLoading: isProfileLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    enabled: hasRecommendationPrefill,
    retry: 1,
  });

  const initialValues = useMemo<TripFormInitialValues>(() => {
    const budget = getParamNumber(searchParams.get('budget'));
    const peopleCount = getParamNumber(searchParams.get('people_count'));

    return {
      destination: searchParams.get('destination') ?? undefined,
      start_date: searchParams.get('start_date') ?? undefined,
      end_date: searchParams.get('end_date') ?? undefined,
      budget: budget ?? null,
      currency: searchParams.get('currency') ?? profile?.preferred_currency ?? undefined,
      people_count: peopleCount,
      departure_city: searchParams.get('departure_city') ?? profile?.origin_city_name ?? undefined,
    };
  }, [profile?.origin_city_name, profile?.preferred_currency, searchParams]);

  const handleSuccess = (trip: Trip) => {
    navigate(`/trips/${trip.id}`, { replace: true });
  };

  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex h-9 w-9 shrink-0 items-center justify-center"
            onClick={handleCancel}
          >
            <ChevronLeft className="h-5 w-5 text-stone-700 dark:text-stone-200" />
          </button>
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Новая поездка
          </h1>
        </div>
      </AppPageHeader>

      <PageContent pb="pb-5" className="pt-5">
        {isProfileLoading ? null : <TripForm initialValues={initialValues} onSuccess={handleSuccess} />}
      </PageContent>
    </PageLayout>
  );
};
