import {
  DestinationDetailSheet,
  RecommendationFiltersUI,
  RecommendationList,
  useRecommendations,
} from '@/features/recommendations';
import type { ScoredDestination } from '@/features/recommendations';
import { profileApi } from '@/features/profile';
import { sendEvent } from '@/shared/api';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

const SkeletonCard = () => (
  <div className="trip-info-card">
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 animate-pulse rounded-2xl bg-[hsl(var(--surface-muted))]" />
        <div>
          <div className="mb-2 h-4 w-32 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
          <div className="h-3 w-20 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
        </div>
      </div>
      <div className="h-12 w-12 animate-pulse rounded-full bg-[hsl(var(--surface-muted))]" />
    </div>
    <div className="flex gap-2">
      <div className="h-6 w-20 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
      <div className="h-6 w-16 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
      <div className="h-6 w-24 animate-pulse rounded-lg bg-[hsl(var(--surface-muted))]" />
    </div>
  </div>
);

export const RecommendationsPage = () => {
  const currentMonth = new Date().getMonth() + 1;
  const [month, setMonth] = useState(currentMonth);
  const [region, setRegion] = useState<string | null>(null);
  const [selected, setSelected] = useState<ScoredDestination | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data, isLoading, isFetching, isError, refetch } = useRecommendations({ month, region });
  useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    retry: 1,
  });

  useEffect(() => {
    if (data?.results && data.results.length > 0) {
      sendEvent('recommendation_shown', {
        recommendation_id: data.recommendation_id,
        model_version: data.model_version,
        count: data.results.length,
        month,
        region: region ?? null,
      });
      data.results.forEach((dest, index) => {
        sendEvent(
          'recommendation_impression',
          {
            recommendation_id: data.recommendation_id,
            model_version: data.model_version,
            destination_id: dest.destination_id,
            score: dest.score,
            rank: index + 1,
            month,
            region: region ?? null,
          },
          'destination',
          dest.destination_id
        );
      });
    }
  }, [data?.model_version, data?.recommendation_id, data?.results, month, region]);

  const handleSelect = (dest: ScoredDestination) => {
    sendEvent(
      'recommendation_clicked',
      {
        recommendation_id: data?.recommendation_id,
        model_version: data?.model_version,
        destination_id: dest.destination_id,
        score: dest.score,
        month,
        region: region ?? null,
      },
      'destination',
      dest.destination_id
    );
    sendEvent(
      'destination_detail_opened',
      {
        recommendation_id: data?.recommendation_id,
        model_version: data?.model_version,
        destination_id: dest.destination_id,
      },
      'destination',
      dest.destination_id
    );
    setSelected(dest);
    setSheetOpen(true);
  };

  const handleMonthChange = (nextMonth: number) => {
    setMonth(nextMonth);
    sendEvent('recommendation_filter_changed', {
      filter: 'month',
      previous_value: month,
      value: nextMonth,
    });
  };

  const handleRegionChange = (nextRegion: string | null) => {
    setRegion(nextRegion);
    sendEvent('recommendation_filter_changed', {
      filter: 'region',
      previous_value: region,
      value: nextRegion,
    });
  };

  const handleSheetClose = () => {
    setSheetOpen(false);
  };

  return (
    <PageLayout>
      <AppPageHeader pb="pb-3">
        <div className="mb-3">
          <h1 className="text-[24px] font-extrabold tracking-tight text-foreground">
            Рекомендации
          </h1>
          <p className="mt-1 text-[14px] font-semibold text-muted-foreground">
            Подобраны под ваши предпочтения
          </p>
        </div>

        <RecommendationFiltersUI
          month={month}
          region={region}
          onMonthChange={handleMonthChange}
          onRegionChange={handleRegionChange}
        />
      </AppPageHeader>

      <PageContent className="pt-4">
        {isLoading || isFetching ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center gap-4 pt-16 text-center">
            <div className="flex h-[72px] w-[72px] items-center justify-center rounded-3xl border border-red-500/20 bg-red-500/10 text-[30px]">
              ⚡
            </div>
            <div>
              <p className="mb-1 text-[16px] font-extrabold text-foreground">
                Не удалось загрузить
              </p>
              <p className="mb-5 text-[13px] font-semibold text-muted-foreground">
                Проверьте подключение и попробуйте снова
              </p>
              <button
                type="button"
                onClick={() => void refetch()}
                className="min-h-11 rounded-2xl bg-primary px-6 text-[14px] font-bold text-primary-foreground shadow-[0_8px_22px_rgba(37,99,235,0.25)]"
              >
                Повторить
              </button>
            </div>
          </div>
        ) : (
          <RecommendationList
            destinations={data?.results ?? []}
            onSelect={handleSelect}
          />
        )}
      </PageContent>

      <DestinationDetailSheet
        destination={selected}
        month={month}
        recommendationId={data?.recommendation_id}
        modelVersion={data?.model_version}
        open={sheetOpen}
        onClose={handleSheetClose}
      />
    </PageLayout>
  );
};
