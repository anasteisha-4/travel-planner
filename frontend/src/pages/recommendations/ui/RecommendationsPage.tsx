import {
  destinationApi,
  type DestinationDetail,
  type DestinationSearchResult,
} from '@/entities/destination';
import { profileApi } from '@/features/profile';
import type { ScoredDestination } from '@/features/recommendations';
import {
  DestinationCheckSearch,
  DestinationDetailSheet,
  RecommendationFiltersUI,
  RecommendationList,
  useDestinationScore,
  useRecommendations,
} from '@/features/recommendations';
import { sendEvent } from '@/shared/api';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { Compass, Map, Route, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const LOADING_MESSAGES = [
  'Сверяем сезон, бюджет и визы',
  'Отбираем лучшие совпадения',
  'Проверяем спорные места',
  'Собираем финальный список',
] as const;

const LOADING_STEPS = [
  { label: 'Профиль', icon: Compass },
  { label: 'Маршруты', icon: Route },
  { label: 'Проверка', icon: Sparkles },
] as const;

const RecommendationsLoadingState = ({ messageIndex }: { messageIndex: number }) => (
  <div className="flex min-h-[430px] flex-col justify-center pb-8">
    <div className="relative overflow-hidden rounded-[28px] border border-[hsl(var(--surface-border))] px-5 py-6 shadow-[0_5px_15px_rgba(15,23,42,0.10)] dark:shadow-[0_5px_15px_rgba(0,0,0,0.28)]">
      <div className="relative mx-auto flex h-36 w-36 items-center justify-center">
        <div className="absolute inset-0 rounded-full border border-primary/15" />
        <div className="absolute inset-3 animate-[spin_9s_linear_infinite] rounded-full border border-dashed border-primary/35" />
        <div className="absolute inset-7 animate-[spin_6s_linear_infinite] rounded-full border border-dashed border-amber-400/45 [animation-direction:reverse]" />
        <div className="absolute left-3 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_18px_rgba(37,99,235,0.55)]" />
        <div className="absolute right-5 top-8 h-2.5 w-2.5 rounded-full bg-amber-400 shadow-[0_0_16px_rgba(251,191,36,0.6)]" />
        <div className="flex h-20 w-20 items-center justify-center rounded-[24px] bg-primary text-primary-foreground shadow-[0_16px_36px_hsl(var(--primary)/0.28)]">
          <Map className="h-9 w-9" />
        </div>
      </div>

      <div className="relative mt-5 text-center">
        <p className="text-[20px] font-extrabold tracking-tight text-foreground">
          Подбираем направления
        </p>
        <p className="mt-2 min-h-5 text-[13px] font-bold text-muted-foreground transition-opacity">
          {LOADING_MESSAGES[messageIndex % LOADING_MESSAGES.length]}
        </p>
      </div>

      <div className="relative mt-6 grid grid-cols-3 gap-2">
        {LOADING_STEPS.map((step, index) => {
          const Icon = step.icon;
          const isActive = index <= messageIndex % LOADING_MESSAGES.length;
          return (
            <div
              key={step.label}
              className="rounded-2xl border border-[hsl(var(--surface-border))] bg-background/70 px-2.5 py-3 text-center backdrop-blur"
            >
              <div
                className={`mx-auto flex h-9 w-9 items-center justify-center rounded-2xl transition ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'bg-[hsl(var(--surface-muted))] text-muted-foreground'
                }`}
              >
                <Icon className="h-[18px] w-[18px]" />
              </div>
              <p className="mt-2 text-[11px] font-extrabold text-foreground">{step.label}</p>
            </div>
          );
        })}
      </div>

      <div className="relative mt-5 h-2 overflow-hidden rounded-full bg-background/70">
        <div className="h-full w-2/5 animate-[recommendation-progress_2.4s_ease-in-out_infinite] rounded-full bg-primary" />
      </div>
    </div>
  </div>
);

const getCheckedDestination = (
  searchResult: DestinationSearchResult,
  detail?: DestinationDetail,
  scored?: ScoredDestination
): ScoredDestination => ({
  ...scored,
  destination_id: searchResult.id,
  name: detail?.name ?? scored?.name ?? searchResult.name,
  name_original: detail?.name_original ?? scored?.name_original ?? searchResult.name_original,
  name_ru: detail?.name_ru ?? scored?.name_ru ?? searchResult.name_ru,
  display_name: detail?.display_name ?? scored?.display_name ?? searchResult.display_name,
  country_code: detail?.country_code ?? scored?.country_code ?? searchResult.country_code,
  region: detail?.region ?? scored?.region ?? 'Каталог направлений',
  score: scored?.score ?? 0.5,
  score_breakdown: scored?.score_breakdown ?? {},
  explanation_tags: scored?.explanation_tags ?? [],
  avg_daily_cost_usd: scored?.avg_daily_cost_usd ?? null,
  avg_daily_cost: scored?.avg_daily_cost,
  avg_daily_cost_currency: scored?.avg_daily_cost_currency,
  avg_daily_budget_usd: scored?.avg_daily_budget_usd,
  avg_daily_budget: scored?.avg_daily_budget,
  avg_daily_budget_currency: scored?.avg_daily_budget_currency,
  route_cost_usd: scored?.route_cost_usd,
  route_cost_source: scored?.route_cost_source,
  season_score: scored?.season_score ?? null,
  safety_score: scored?.safety_score ?? detail?.safety_score ?? null,
});

export const RecommendationsPage = () => {
  const currentMonth = new Date().getMonth() + 1;
  const [month, setMonth] = useState(currentMonth);
  const [region, setRegion] = useState<string | null>(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState<ScoredDestination | null>(
    null
  );
  const [selectedCheckResult, setSelectedCheckResult] = useState<DestinationSearchResult | null>(
    null
  );
  const [sheetMode, setSheetMode] = useState<'recommendation' | 'check'>('recommendation');
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  const trackedEmptyStates = useRef<Set<string>>(new Set());

  const { data, isLoading, isFetching, isError, refetch } = useRecommendations({ month, region });
  const showLoadingState = isLoading || (isFetching && !data);
  const displayedLoadingMessageIndex = showLoadingState ? loadingMessageIndex : 0;
  const { data: checkedDestinationDetail } = useQuery({
    queryKey: ['destination-detail', selectedCheckResult?.id],
    queryFn: () => destinationApi.getDestination(selectedCheckResult?.id ?? ''),
    enabled: !!selectedCheckResult?.id,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
  const selectedRecommendationMatch = selectedCheckResult
    ? data?.results.find((destination) => destination.destination_id === selectedCheckResult.id)
    : undefined;
  const { data: checkedDestinationScore, isLoading: isDestinationScoreLoading } =
    useDestinationScore(
      selectedCheckResult
        ? {
            destination_id: selectedCheckResult.id,
            travel_month: month,
            citizenship_code: 'RU',
          }
        : null
    );
  useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    retry: 1,
  });

  const checkedDestination = selectedCheckResult
    ? getCheckedDestination(
        selectedCheckResult,
        checkedDestinationDetail,
        checkedDestinationScore ?? selectedRecommendationMatch
      )
    : null;
  const sheetDestination = sheetMode === 'check' ? checkedDestination : selectedRecommendation;
  const isSheetLoading =
    sheetMode === 'check' && !selectedRecommendationMatch && isDestinationScoreLoading;

  useEffect(() => {
    if (!showLoadingState) {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      setLoadingMessageIndex((current) => current + 1);
    }, 2200);
    return () => window.clearInterval(intervalId);
  }, [showLoadingState]);

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
    if (data?.results && data.results.length === 0) {
      const key = `${data.recommendation_id}:${data.model_version}:${month}:${region ?? 'all'}`;
      if (trackedEmptyStates.current.has(key)) return;
      trackedEmptyStates.current.add(key);
      sendEvent('recommendation_empty_state_shown', {
        recommendation_id: data.recommendation_id,
        model_version: data.model_version,
        month,
        region: region ?? null,
        reason: 'no_results',
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
    setSelectedRecommendation(dest);
    setSheetMode('recommendation');
    setSheetOpen(true);
  };

  const handleCheckSelect = (dest: DestinationSearchResult) => {
    sendEvent(
      'destination_detail_opened',
      {
        destination_id: dest.id,
        source: 'recommendation_check_search',
      },
      'destination',
      dest.id
    );
    setSelectedCheckResult(dest);
    setSheetMode('check');
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

        <div className="mb-3">
          <DestinationCheckSearch onSelect={handleCheckSelect} />
        </div>

        <RecommendationFiltersUI
          month={month}
          region={region}
          onMonthChange={handleMonthChange}
          onRegionChange={handleRegionChange}
        />
      </AppPageHeader>

      <PageContent className="pt-4">
        {showLoadingState ? (
          <RecommendationsLoadingState messageIndex={displayedLoadingMessageIndex} />
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
          <RecommendationList destinations={data?.results ?? []} onSelect={handleSelect} />
        )}
      </PageContent>

      <DestinationDetailSheet
        destination={sheetDestination}
        month={month}
        recommendationId={sheetMode === 'recommendation' ? data?.recommendation_id : undefined}
        modelVersion={sheetMode === 'recommendation' ? data?.model_version : undefined}
        open={sheetOpen}
        isLoading={isSheetLoading}
        onClose={handleSheetClose}
      />
    </PageLayout>
  );
};
