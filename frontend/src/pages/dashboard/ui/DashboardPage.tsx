import { useProfile } from '@/entities/user';
import { TripsPreview } from '@/features/trips';
import { useIsOnline } from '@/shared/lib';
import { PageHeader } from '@/shared/ui';
import { WifiOff } from 'lucide-react';
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

  const isOnline = useIsOnline();
  const { profile, loading } = useProfile(handleUnauthenticated);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="mb-4 h-12 w-12 rounded-full bg-primary/20" />
          <div className="h-4 w-32 rounded bg-primary/20" />
        </div>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 space-y-6 px-4 pb-20">
      <PageHeader className="justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">
          Привет, {profile.login}!<br />
          Отправимся в новое путешествие?
        </h1>
        {!isOnline && (
          <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-border/50 bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
            <WifiOff className="h-3 w-3" />
            Офлайн
          </span>
        )}
      </PageHeader>

      <TripsPreview />
    </div>
  );
};
