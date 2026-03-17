import { useProfile } from '@/entities/user';
import { LogoutButton, authApi } from '@/features/auth';
import { PreferencesEditor, PreferencesView, usePreferences } from '@/features/profile';
import { AppPageHeader, Button, EmptyState, PageContent, PageLayout, SectionLabel } from '@/shared/ui';
import { ClipboardList, Loader2, Pencil } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);

  const handleUnauthenticated = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login', { replace: true });
    } else {
      navigate('/onboarding', { replace: true });
    }
  }, [navigate]);

  const { profile, loading } = useProfile(handleUnauthenticated);
  const { preferences, hasPreferences, isFetching, refetch } = usePreferences();

  const handleLogout = useCallback(async () => {
    await authApi.logout();
    navigate('/login', { replace: true });
  }, [navigate]);

  const handleSaved = () => {
    refetch();
    setIsEditing(false);
  };

  if (loading) {
    return (
      <PageLayout>
        <AppPageHeader pb="pb-3">
          <div className="h-7 w-24 animate-pulse rounded-lg bg-stone-100 dark:bg-stone-800" />
        </AppPageHeader>
        <PageContent pb="pb-0" className="pt-2">
          <div className="trip-info-card animate-pulse">
            <div className="h-4 w-full rounded bg-stone-100 dark:bg-stone-800" />
          </div>
        </PageContent>
      </PageLayout>
    );
  }

  if (!profile) return null;

  return (
    <PageLayout>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center justify-between">
          <h1 className="text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Профиль
          </h1>
          <LogoutButton onLogout={handleLogout} />
        </div>
      </AppPageHeader>

      <PageContent>
        <div className="flex flex-col gap-6">
          <div>
            <SectionLabel className="mb-2">Аккаунт</SectionLabel>
            <div className="trip-info-card flex flex-col gap-0">
              <div className="flex items-center justify-between py-1">
                <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  Логин
                </span>
                <span className="text-[15px] font-bold text-primary">{profile.login}</span>
              </div>
              <div className="my-2 h-px bg-stone-100 dark:bg-stone-800" />
              <div className="flex items-center justify-between py-1">
                <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  Email
                </span>
                <span className="text-[15px] font-semibold text-stone-900 dark:text-white">
                  {profile.email}
                </span>
              </div>
            </div>
          </div>

          <div>
            <SectionLabel
              className="mb-2"
              action={
                hasPreferences ? (
                  <button
                    type="button"
                    onClick={() => setIsEditing(true)}
                    className="flex h-[30px] items-center gap-1.5 rounded-xl bg-stone-100 px-3 text-[13px] font-semibold text-stone-600 disabled:opacity-40 dark:bg-stone-800 dark:text-stone-300"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Изменить
                  </button>
                ) : undefined
              }
            >
              Предпочтения
            </SectionLabel>

            {isFetching ? (
              <div className="trip-info-card flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-stone-300 dark:text-stone-600" />
              </div>
            ) : hasPreferences ? (
              <PreferencesView preferences={preferences} />
            ) : (
              <div className="flex flex-col gap-3">
                <EmptyState icon={ClipboardList} message="Анкета предпочтений еще не заполнена" />
                <Button onClick={() => setIsEditing(true)} className="h-[52px] flex-1 rounded-2xl">
                  Указать предпочтения
                </Button>
              </div>
            )}
          </div>
        </div>
      </PageContent>

      <PreferencesEditor
        open={isEditing}
        onOpenChange={setIsEditing}
        initialData={preferences}
        onSaved={handleSaved}
      />
    </PageLayout>
  );
};
