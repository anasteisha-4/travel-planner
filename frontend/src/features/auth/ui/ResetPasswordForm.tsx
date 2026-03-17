import {
  AppInput,
  AppPageHeader,
  FieldLabel,
  FormError,
  PageContent,
  PageLayout,
} from '@/shared/ui';
import { CheckCircle2, ChevronLeft, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useResetPassword } from '../model/useResetPassword';

export const ResetPasswordForm = ({ onLoginClick }: { onLoginClick: () => void }) => {
  const {
    token,
    newPassword,
    confirmPassword,
    showPassword,
    setShowPassword,
    setNewPassword,
    setConfirmPassword,
    isLoading,
    isSuccess,
    fieldErrors,
    handleSubmit,
  } = useResetPassword();

  if (!token) {
    return (
      <PageLayout fullScreen className="items-center justify-center">
        <div className="flex flex-col items-center gap-4 px-5 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 dark:bg-red-900/20">
            <ChevronLeft className="h-6 w-6 text-red-400" />
          </div>
          <h1 className="text-[20px] font-extrabold tracking-tight text-stone-900 dark:text-white">
            Недействительная ссылка
          </h1>
          <p className="text-[14px] text-stone-400 dark:text-stone-500">
            Ссылка для сброса пароля недействительна или истекла. Запросите новую ссылку.
          </p>
          <button
            type="button"
            onClick={onLoginClick}
            className="mt-2 flex h-[52px] w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-semibold text-white shadow-[0_4px_16px_rgba(37,99,235,0.28)]"
          >
            Вернуться к входу
          </button>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-6" className="flex flex-col items-center">
        <img
          src="/assets/logo.png"
          alt="Triply"
          className="mb-4 h-16 w-16 object-contain drop-shadow-sm"
        />
        <h1 className="text-center text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
          {isSuccess ? 'Пароль обновлён' : 'Новый пароль'}
        </h1>
        <p className="mt-1 text-center text-[14px] font-medium text-stone-400 dark:text-stone-500">
          {isSuccess ? 'Можете войти в аккаунт' : 'Придумайте новый пароль для вашего аккаунта'}
        </p>
      </AppPageHeader>

      <PageContent pb="pb-4">
        {isSuccess ? (
          <div className="flex flex-col items-center gap-4 pt-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-green-50 dark:bg-green-900/20">
              <CheckCircle2 className="h-6 w-6 text-green-500" />
            </div>
            <p className="text-center text-[14px] text-stone-400 dark:text-stone-500">
              Пароль успешно изменён.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <div>
              <FieldLabel>Новый пароль</FieldLabel>
              <div className="relative">
                <AppInput
                  id="new_password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isLoading}
                  error={!!fieldErrors.new_password}
                  className="pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-stone-400 transition-colors active:text-stone-700 dark:active:text-stone-200"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <FormError message={fieldErrors.new_password} />
            </div>

            <div>
              <FieldLabel>Подтвердите пароль</FieldLabel>
              <AppInput
                id="confirm_password"
                type={showPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isLoading}
                error={!!fieldErrors.confirm_password}
              />
              <FormError message={fieldErrors.confirm_password} />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="flex h-[52px] w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-semibold text-white shadow-[0_4px_16px_rgba(37,99,235,0.28)] disabled:opacity-60"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Сбросить пароль
            </button>
          </form>
        )}
      </PageContent>

      <div
        className="shrink-0 border-t border-stone-100 px-5 py-4 dark:border-stone-800"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)' }}
      >
        <button
          type="button"
          onClick={onLoginClick}
          className="flex h-[52px] w-full items-center justify-center gap-1.5 rounded-2xl border border-stone-200 bg-stone-100 text-[15px] font-semibold text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
        >
          <ChevronLeft className="h-5 w-5" />
          {isSuccess ? 'Войти' : 'Вернуться к входу'}
        </button>
      </div>
    </PageLayout>
  );
};
