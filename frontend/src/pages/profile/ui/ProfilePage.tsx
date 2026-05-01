import { useDeleteAccount, useProfile } from '@/entities/user';
import { LogoutButton, authApi } from '@/features/auth';
import { PreferencesView, usePreferences } from '@/features/profile';
import {
  AppPageHeader,
  Button,
  ConfirmDrawer,
  EmptyState,
  PageContent,
  PageLayout,
  SectionLabel,
  useToast,
} from '@/shared/ui';
import { ProfileEditWizard } from '@/widgets/profile-edit-wizard';
import { ClipboardList, Loader2, Pencil, Trash2 } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteDrawerOpen, setIsDeleteDrawerOpen] = useState(false);
  const { toast } = useToast();

  const handleUnauthenticated = useCallback(() => {
    navigate('/login', { replace: true });
  }, [navigate]);

  const { profile: authProfile, loading } = useProfile(handleUnauthenticated);
  const { profile, hasPreferences, isFetching } = usePreferences();

  const { deleteAccount, isLoading: isDeleting } = useDeleteAccount(
    () => navigate('/login', { replace: true }),
    () => {
      setIsDeleteDrawerOpen(false);
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Не удалось удалить аккаунт. Попробуйте позже.',
      });
    }
  );

  const handleLogout = useCallback(async () => {
    await authApi.logout();
    navigate('/login', { replace: true });
  }, [navigate]);

  const handleSaved = () => setIsEditing(false);

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

  if (!authProfile) return null;

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
                <span className="text-[15px] font-bold text-primary">{authProfile.login}</span>
              </div>
              <div className="my-2 h-px bg-stone-100 dark:bg-stone-800" />
              <div className="flex items-center justify-between py-1">
                <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  Email
                </span>
                <span className="text-[15px] font-semibold text-stone-900 dark:text-white">
                  {authProfile.email}
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
            ) : hasPreferences && profile ? (
              <PreferencesView preferences={profile} />
            ) : (
              <div className="flex flex-col gap-3">
                <EmptyState icon={ClipboardList} message="Анкета предпочтений еще не заполнена" />
                <Button
                  onClick={() => navigate('/onboarding')}
                  className="h-[52px] flex-1 rounded-2xl"
                >
                  Заполнить анкету
                </Button>
              </div>
            )}
          </div>

          <div className="mb-4">
            <button
              type="button"
              onClick={() => setIsDeleteDrawerOpen(true)}
              className="flex w-full items-center gap-3 rounded-2xl border border-red-100 bg-red-50/60 px-4 py-3.5 text-left transition-colors active:bg-red-100/80 dark:border-red-900/40 dark:bg-red-900/10"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-red-100/80 bg-red-50 dark:border-red-900/60 dark:bg-red-900/20">
                <Trash2 className="h-4 w-4 text-red-500" />
              </div>
              <div className="flex flex-col">
                <span className="text-[15px] font-semibold text-red-600 dark:text-red-400">
                  Удалить аккаунт
                </span>
              </div>
            </button>
          </div>
        </div>
      </PageContent>

      {isEditing && profile && (
        <ProfileEditWizard
          open={isEditing}
          onOpenChange={setIsEditing}
          initialData={profile}
          onSaved={handleSaved}
        />
      )}

      <ConfirmDrawer
        open={isDeleteDrawerOpen}
        onOpenChange={setIsDeleteDrawerOpen}
        variant="delete"
        title="Удалить аккаунт?"
        description="Все данные профиля, поездки и расходы будут удалены безвозвратно."
        confirmLabel="Удалить аккаунт"
        cancelLabel="Отмена"
        onConfirm={deleteAccount}
        loading={isDeleting}
      />
    </PageLayout>
  );
};
