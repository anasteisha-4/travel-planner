import {
  DestinationDetailSheet,
  RecommendationFiltersUI,
  RecommendationList,
  useRecommendations,
} from '@/features/recommendations';
import type { ScoredDestination } from '@/features/recommendations';
import { sendEvent } from '@/shared/api';
import { AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { useEffect, useState } from 'react';

const SkeletonCard = () => (
  <div
    style={{
      background: '#fff',
      border: '1px solid rgba(0,0,0,0.06)',
      borderRadius: 20,
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      padding: 16,
    }}
  >
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 44, height: 44, borderRadius: 14, background: 'rgba(28,25,23,0.06)', animation: 'pulse 1.5s ease-in-out infinite' }} />
        <div>
          <div style={{ width: 120, height: 14, borderRadius: 6, background: 'rgba(28,25,23,0.06)', marginBottom: 6, animation: 'pulse 1.5s ease-in-out infinite' }} />
          <div style={{ width: 70, height: 11, borderRadius: 6, background: 'rgba(28,25,23,0.04)', animation: 'pulse 1.5s ease-in-out infinite' }} />
        </div>
      </div>
      <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(28,25,23,0.06)', animation: 'pulse 1.5s ease-in-out infinite' }} />
    </div>
    <div style={{ display: 'flex', gap: 6 }}>
      <div style={{ width: 70, height: 22, borderRadius: 8, background: 'rgba(28,25,23,0.04)', animation: 'pulse 1.5s ease-in-out infinite' }} />
      <div style={{ width: 60, height: 22, borderRadius: 8, background: 'rgba(28,25,23,0.04)', animation: 'pulse 1.5s ease-in-out infinite' }} />
      <div style={{ width: 80, height: 22, borderRadius: 8, background: 'rgba(28,25,23,0.04)', animation: 'pulse 1.5s ease-in-out infinite' }} />
    </div>
  </div>
);

export const RecommendationsPage = () => {
  const currentMonth = new Date().getMonth() + 1;
  const [month, setMonth] = useState(currentMonth);
  const [region, setRegion] = useState<string | null>(null);
  const [selected, setSelected] = useState<ScoredDestination | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data, isLoading, isError, refetch } = useRecommendations({ month, region });

  useEffect(() => {
    if (data?.results && data.results.length > 0) {
      sendEvent('recommendation_shown', {
        recommendation_id: data.recommendation_id,
        model_version: data.model_version,
        count: data.results.length,
        month,
        region: region ?? null,
      });
    }
  }, [data?.recommendation_id]);

  const handleSelect = (dest: ScoredDestination) => {
    sendEvent('recommendation_clicked', { destination_id: dest.destination_id, score: dest.score, month }, 'destination', dest.destination_id);
    sendEvent('destination_detail_opened', { destination_id: dest.destination_id }, 'destination', dest.destination_id);
    setSelected(dest);
    setSheetOpen(true);
  };

  const handleSheetClose = () => {
    setSheetOpen(false);
  };

  return (
    <PageLayout>
      <AppPageHeader pb="pb-3">
        <div style={{ marginBottom: 14 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: '#1C1917',
              letterSpacing: '-0.02em',
              fontFamily: 'Manrope, sans-serif',
              marginBottom: 2,
            }}
          >
            Рекомендации
          </h1>
          <p style={{ fontSize: 14, fontWeight: 500, color: '#A8A29E', fontFamily: 'Manrope, sans-serif' }}>
            Подобраны под ваши предпочтения
          </p>
        </div>

        <RecommendationFiltersUI
          month={month}
          region={region}
          onMonthChange={setMonth}
          onRegionChange={setRegion}
        />
      </AppPageHeader>

      <PageContent className="pt-4">
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[0, 1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : isError ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              paddingTop: 64,
              gap: 16,
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 24,
                background: 'rgba(239,68,68,0.07)',
                border: '1px solid rgba(239,68,68,0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 32,
              }}
            >
              ⚡
            </div>
            <div>
              <p
                style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: '#1C1917',
                  marginBottom: 4,
                  fontFamily: 'Manrope, sans-serif',
                }}
              >
                Не удалось загрузить
              </p>
              <p
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: '#A8A29E',
                  marginBottom: 20,
                  fontFamily: 'Manrope, sans-serif',
                }}
              >
                Проверьте подключение и попробуйте снова
              </p>
              <button
                type="button"
                onClick={() => void refetch()}
                style={{
                  height: 44,
                  paddingInline: 24,
                  borderRadius: 14,
                  background: '#2563EB',
                  border: 'none',
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 700,
                  fontFamily: 'Manrope, sans-serif',
                  cursor: 'pointer',
                  boxShadow: '0 4px 16px rgba(37,99,235,0.28)',
                }}
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
        open={sheetOpen}
        onClose={handleSheetClose}
      />
    </PageLayout>
  );
};
