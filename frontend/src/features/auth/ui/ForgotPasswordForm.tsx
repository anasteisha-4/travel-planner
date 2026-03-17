import {
  AppInput,
  AppPageHeader,
  FieldLabel,
  FormError,
  PageContent,
  PageLayout,
} from '@/shared/ui';
import { ChevronLeft, Loader2, MailCheck } from 'lucide-react';
import { useForgotPassword } from '../model/useForgotPassword';

export const ForgotPasswordForm = ({ onBackToLogin }: { onBackToLogin: () => void }) => {
  const { email, setEmail, isLoading, isSent, fieldErrors, handleSubmit } = useForgotPassword();

  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-6" className="flex flex-col items-center">
        <img
          src="/assets/logo.png"
          alt="Triply"
          className="mb-4 h-16 w-16 object-contain drop-shadow-sm"
        />
        <h1 className="text-center text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
          {isSent ? 'Проверьте почту' : 'Сброс пароля'}
        </h1>
        <p className="mt-1 text-center text-[14px] font-medium text-stone-400 dark:text-stone-500">
          {isSent
            ? 'Мы отправили письмо с инструкциями'
            : 'Введите почту — пришлём ссылку для сброса'}
        </p>
      </AppPageHeader>

      <PageContent pb="pb-4">
        {isSent ? (
          <div className="flex flex-col items-center gap-4 pt-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 dark:bg-primary/20">
              <MailCheck className="h-6 w-6 text-primary" />
            </div>
            <p className="text-center text-[14px] leading-relaxed text-stone-500 dark:text-stone-400">
              Если аккаунт с адресом{' '}
              <span className="font-semibold text-stone-900 dark:text-white">{email}</span>{' '}
              существует, вы получите письмо со ссылкой для сброса пароля.{' '}
              <span className="text-stone-400">Ссылка действительна 20 минут.</span>
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <div>
              <FieldLabel>Почта</FieldLabel>
              <AppInput
                id="email"
                type="email"
                placeholder="email@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                error={!!fieldErrors.email}
              />
              <FormError message={fieldErrors.email} />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="flex h-[52px] w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-semibold text-white shadow-[0_4px_16px_rgba(37,99,235,0.28)] disabled:opacity-60"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Отправить ссылку
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
          disabled={isLoading}
          onClick={onBackToLogin}
          className="flex h-[52px] w-full items-center justify-center gap-1.5 rounded-2xl border border-stone-200 bg-stone-100 text-[15px] font-semibold text-stone-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
        >
          <ChevronLeft className="h-5 w-5" />
          Вернуться к входу
        </button>
      </div>
    </PageLayout>
  );
};
