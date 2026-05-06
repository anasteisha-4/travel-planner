import { useProfile } from '@/entities/user';
import { TripsPreview } from '@/features/trips';
import { ActionCard, AppPageHeader, PageContent, PageLayout } from '@/shared/ui';
import { MapPin } from 'lucide-react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

export const DashboardPage = () => {
  const navigate = useNavigate();

  const handleUnauthenticated = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login', { replace: true });
    } else {
      navigate('/onboarding', { replace: true });
    }
  }, [navigate]);

  const { profile, loading } = useProfile(handleUnauthenticated);

  if (loading) {
    return (
      <PageLayout>
        <AppPageHeader pb="pb-3">
          <div className="h-4 w-20 animate-pulse rounded-lg bg-stone-100 dark:bg-[hsl(var(--surface-muted))]" />
          <div className="mt-1.5 h-7 w-40 animate-pulse rounded-lg bg-stone-100 dark:bg-[hsl(var(--surface-muted))]" />
        </AppPageHeader>
      </PageLayout>
    );
  }

  if (!profile) return null;

  return (
    <PageLayout>
      <AppPageHeader>
        <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
          Добро пожаловать, {profile.login}!
        </h1>
        <p className="text-[14px] font-medium text-stone-400 dark:text-stone-500">
          Отправимся в новое путешествие?
        </p>
      </AppPageHeader>

      <PageContent>
        <div className="flex flex-col gap-5">
          <ActionCard
            icon={MapPin}
            title="Новая поездка"
            subtitle="Начните планировать маршрут"
            onClick={() => navigate('/trips/new')}
          />
          <TripsPreview />
        </div>
      </PageContent>
    </PageLayout>
  );
};
