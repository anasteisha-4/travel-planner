import { AppInput, AuthForm, FieldLabel, FormError } from '@/shared/ui';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useLogin } from '../model/useLogin';

export const LoginForm = ({
  oauthCallback = false,
  onSuccess,
  onRegisterClick,
  onForgotPasswordClick,
  onError,
}: {
  oauthCallback?: boolean;
  onSuccess: () => void;
  onRegisterClick: () => void;
  onForgotPasswordClick: () => void;
  onError?: () => void;
}) => {
  const {
    identifier,
    setIdentifier,
    password,
    setPassword,
    showPassword,
    setShowPassword,
    isLoading,
    fieldErrors,
    handleSubmit,
    handleYandexLogin,
  } = useLogin({ oauthCallback, onSuccess, onError });

  if (oauthCallback) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <AuthForm
      title="Triply"
      description="Войдите, чтобы продолжить"
      onSubmit={handleSubmit}
      onYandexLogin={handleYandexLogin}
      footerText="Нет аккаунта?"
      footerLinkText="Зарегистрироваться"
      onFooterLinkClick={onRegisterClick}
      isLoading={isLoading}
    >
      <div>
        <FieldLabel>Логин или почта</FieldLabel>
        <AppInput
          id="identifier"
          type="text"
          placeholder="email@example.com"
          required
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          disabled={isLoading}
          error={!!fieldErrors.identifier}
        />
        <FormError message={fieldErrors.identifier} />
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between">
          <FieldLabel className="mb-0">Пароль</FieldLabel>
          <button
            type="button"
            onClick={onForgotPasswordClick}
            className="text-[12px] font-semibold text-primary"
          >
            Забыли пароль?
          </button>
        </div>
        <div className="relative">
          <AppInput
            id="password"
            type={showPassword ? 'text' : 'password'}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            error={!!fieldErrors.password}
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
        <FormError message={fieldErrors.password} />
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="flex h-[52px] w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-semibold text-white shadow-[0_4px_16px_rgba(37,99,235,0.28)] transition-all disabled:opacity-60"
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Войти
      </button>
    </AuthForm>
  );
};
