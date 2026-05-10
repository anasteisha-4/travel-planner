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
import { sendEvent } from '@/shared/api';
import { HAPTIC_SINGLE_ERROR, HAPTIC_SINGLE_TAP, useHapticFeedback } from '@/shared/lib/useHapticFeedback';
import { ClipboardList, Pencil, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const SkeletonLine = ({ className }: { className: string }) => (
  <div className={`animate-pulse rounded-full bg-[hsl(var(--surface-muted))] ${className}`} />
);

const ProfilePageSkeleton = () => (
  <PageLayout>
    <AppPageHeader pb="pb-3">
      <div className="flex items-center justify-between">
        <SkeletonLine className="h-8 w-28" />
        <div className="flex h-10 items-center gap-2 rounded-2xl px-3 text-red-500/40">
          <SkeletonLine className="h-5 w-5 bg-red-500/15" />
          <SkeletonLine className="h-5 w-16 bg-red-500/15" />
        </div>
      </div>
    </AppPageHeader>

    <PageContent>
      <div className="flex flex-col gap-6">
        <div>
          <SkeletonLine className="mb-2 h-3 w-20" />
          <div className="trip-info-card flex flex-col gap-0">
            <div className="flex items-center justify-between gap-4 py-1">
              <SkeletonLine className="h-3 w-14" />
              <SkeletonLine className="h-5 w-16 bg-primary/20" />
            </div>
            <div className="my-3 h-px bg-[hsl(var(--surface-border))]" />
            <div className="flex items-center justify-between gap-4 py-1">
              <SkeletonLine className="h-3 w-12" />
              <SkeletonLine className="h-5 w-36 max-w-[54%]" />
            </div>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <SkeletonLine className="h-3 w-32" />
            <div className="flex h-[30px] items-center gap-1.5 rounded-xl bg-[hsl(var(--surface-muted))] px-3">
              <SkeletonLine className="h-3.5 w-3.5 bg-[hsl(var(--surface-field))]" />
              <SkeletonLine className="h-4 w-16 bg-[hsl(var(--surface-field))]" />
            </div>
          </div>
          <div className="trip-info-card flex flex-col gap-0 pb-1">
            <div className="pb-1">
              <SkeletonLine className="mb-3 h-3 w-24" />
              <div className="flex flex-wrap gap-1.5">
                {[0, 1, 2].map((item) => (
                  <div
                    key={item}
                    className={`flex h-9 items-center gap-2 rounded-xl border border-[hsl(var(--surface-border))] bg-primary/5 px-3 ${
                      item === 0 ? 'w-32' : 'w-28'
                    }`}
                  >
                    <SkeletonLine className="h-5 w-5 shrink-0 bg-primary/20" />
                    <SkeletonLine className="h-4 flex-1 bg-primary/20" />
                  </div>
                ))}
              </div>
            </div>

            <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

            <div className="flex flex-col gap-0">
              {[
                { labelClassName: 'w-24', valueClassName: 'w-20' },
                { labelClassName: 'w-24', valueClassName: 'w-32' },
                { labelClassName: 'w-36', valueClassName: 'w-16' },
                { labelClassName: 'w-32', valueClassName: 'w-36' },
              ].map((item, index, items) => (
                <div key={index}>
                  <div className="flex items-center justify-between py-2">
                    <SkeletonLine className={`h-3 ${item.labelClassName}`} />
                    <SkeletonLine className={`h-5 ${item.valueClassName}`} />
                  </div>
                  {index < items.length - 1 && <div className="h-px bg-[hsl(var(--surface-field))]" />}
                </div>
              ))}
            </div>

            <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

            <SkeletonLine className="mb-3 h-3 w-32" />
            <div className="mb-3 flex flex-wrap gap-1.5">
              {[0, 1, 2].map((item) => (
                <div
                  key={item}
                  className="flex h-8 items-center gap-2 rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3"
                >
                  <SkeletonLine className="h-4 w-4 bg-[hsl(var(--surface-field))]" />
                  <SkeletonLine className="h-4 w-16 bg-[hsl(var(--surface-field))]" />
                </div>
              ))}
            </div>

            <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

            <SkeletonLine className="mb-3 h-3 w-40" />
            <div className="flex flex-col gap-2">
              {['w-28', 'w-14', 'w-16'].map((labelClassName) => (
                <div
                  key={labelClassName}
                  className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5"
                >
                  <SkeletonLine className={`h-4 ${labelClassName} bg-[hsl(var(--surface-field))]`} />
                  <SkeletonLine className="h-5 w-28 bg-[hsl(var(--surface-field))]" />
                </div>
              ))}
            </div>

            <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

            <SkeletonLine className="mb-3 h-3 w-24" />
            <SkeletonLine className="h-9 w-36 rounded-xl" />
          </div>
        </div>

        <div className="mb-4">
          <div className="flex w-full items-center gap-3 rounded-2xl border border-red-500/10 bg-red-500/5 px-4 py-3.5">
            <SkeletonLine className="h-9 w-9 shrink-0 rounded-xl bg-red-500/10" />
            <SkeletonLine className="h-5 w-36 bg-red-500/10" />
          </div>
        </div>
      </div>
    </PageContent>
  </PageLayout>
);

const ProfilePreferencesSkeleton = () => (
  <div className="trip-info-card flex flex-col gap-0 pb-1">
    <div className="pb-1">
      <SkeletonLine className="mb-3 h-3 w-24" />
      <div className="flex flex-wrap gap-1.5">
        {[0, 1, 2].map((item) => (
          <div
            key={item}
            className={`flex h-9 items-center gap-2 rounded-xl border border-[hsl(var(--surface-border))] bg-primary/5 px-3 ${
              item === 0 ? 'w-32' : 'w-28'
            }`}
          >
            <SkeletonLine className="h-5 w-5 shrink-0 bg-primary/20" />
            <SkeletonLine className="h-4 flex-1 bg-primary/20" />
          </div>
        ))}
      </div>
    </div>

    <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

    <div className="flex flex-col gap-0">
      {[
        { labelClassName: 'w-24', valueClassName: 'w-20' },
        { labelClassName: 'w-24', valueClassName: 'w-32' },
        { labelClassName: 'w-36', valueClassName: 'w-16' },
        { labelClassName: 'w-32', valueClassName: 'w-36' },
      ].map((item, index, items) => (
        <div key={index}>
          <div className="flex items-center justify-between py-2">
            <SkeletonLine className={`h-3 ${item.labelClassName}`} />
            <SkeletonLine className={`h-5 ${item.valueClassName}`} />
          </div>
          {index < items.length - 1 && <div className="h-px bg-[hsl(var(--surface-field))]" />}
        </div>
      ))}
    </div>

    <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

    <SkeletonLine className="mb-3 h-3 w-32" />
    <div className="mb-3 flex flex-wrap gap-1.5">
      {[0, 1, 2].map((item) => (
        <div
          key={item}
          className="flex h-8 items-center gap-2 rounded-xl border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-muted))] px-3"
        >
          <SkeletonLine className="h-4 w-4 bg-[hsl(var(--surface-field))]" />
          <SkeletonLine className="h-4 w-16 bg-[hsl(var(--surface-field))]" />
        </div>
      ))}
    </div>

    <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

    <SkeletonLine className="mb-3 h-3 w-40" />
    <div className="flex flex-col gap-2">
      {['w-28', 'w-14', 'w-16'].map((labelClassName) => (
        <div
          key={labelClassName}
          className="flex items-center justify-between rounded-xl bg-[hsl(var(--surface-muted))] px-3 py-2.5"
        >
          <SkeletonLine className={`h-4 ${labelClassName} bg-[hsl(var(--surface-field))]`} />
          <SkeletonLine className="h-5 w-28 bg-[hsl(var(--surface-field))]" />
        </div>
      ))}
    </div>

    <div className="my-3 h-px bg-[hsl(var(--surface-field))]" />

    <SkeletonLine className="mb-3 h-3 w-24" />
    <SkeletonLine className="h-9 w-36 rounded-xl" />
  </div>
);

export const ProfilePage = () => {
  const navigate = useNavigate();
  const { play } = useHapticFeedback();
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteDrawerOpen, setIsDeleteDrawerOpen] = useState(false);
  const didTrackProfileView = useRef(false);
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

  useEffect(() => {
    if (!authProfile || didTrackProfileView.current) return;
    didTrackProfileView.current = true;
    sendEvent('profile_viewed', {
      has_preferences: hasPreferences,
      onboarding_completed: profile?.onboarding_completed ?? false,
      preferred_currency: profile?.preferred_currency ?? null,
    });
  }, [authProfile, hasPreferences, profile?.onboarding_completed, profile?.preferred_currency]);

  const handleSaved = () => setIsEditing(false);

  if (loading) {
    return <ProfilePageSkeleton />;
  }

  if (!authProfile) return null;

  return (
    <PageLayout>
      <AppPageHeader pb="pb-3">
        <div className="flex items-center justify-between">
          <h1 className="text-[22px] font-extrabold tracking-tight text-foreground">
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
              <div className="my-2 h-px bg-[hsl(var(--surface-border))]" />
              <div className="flex items-center justify-between py-1">
                <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400 dark:text-stone-500">
                  Email
                </span>
                <span className="break-words text-right text-[15px] font-semibold text-foreground">
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
                    onClick={() => {
                      play(HAPTIC_SINGLE_TAP);
                      setIsEditing(true);
                    }}
                    className="flex h-[30px] items-center gap-1.5 rounded-xl bg-[hsl(var(--surface-muted))] px-3 text-[13px] font-semibold text-muted-foreground disabled:opacity-40"
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
              <ProfilePreferencesSkeleton />
            ) : hasPreferences && profile ? (
              <PreferencesView preferences={profile} />
            ) : (
              <div className="flex flex-col gap-3">
                <EmptyState icon={ClipboardList} message="Анкета предпочтений еще не заполнена" />
                <Button
                  haptic={HAPTIC_SINGLE_TAP}
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
              onClick={() => {
                play(HAPTIC_SINGLE_ERROR);
                setIsDeleteDrawerOpen(true);
              }}
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
