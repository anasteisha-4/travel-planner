import { AppInput, AuthForm, FieldLabel, FormError } from '@/shared/ui';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useRegister } from '../model/useRegister';

export const RegisterForm = ({
  onSuccess,
  onLoginClick,
}: {
  onSuccess: () => void;
  onLoginClick: () => void;
}) => {
  const {
    formData,
    handleChange,
    fieldErrors,
    isLoading,
    showPassword,
    setShowPassword,
    handleSubmit,
    handleYandexLogin,
  } = useRegister({ onSuccess });

  return (
    <AuthForm
      title="Присоединяйтесь"
      description="Создайте аккаунт и начните планировать путешествия"
      onSubmit={handleSubmit}
      onYandexLogin={handleYandexLogin}
      footerText="Уже есть аккаунт?"
      footerLinkText="Войти"
      onFooterLinkClick={onLoginClick}
      isLoading={isLoading}
    >
      <div>
        <FieldLabel>Логин</FieldLabel>
        <AppInput
          id="login"
          type="text"
          required
          value={formData.login}
          onChange={handleChange}
          disabled={isLoading}
          error={!!fieldErrors.login}
        />
        <FormError message={fieldErrors.login} />
      </div>

      <div>
        <FieldLabel>Почта</FieldLabel>
        <AppInput
          id="email"
          type="email"
          placeholder="email@example.com"
          required
          value={formData.email}
          onChange={handleChange}
          disabled={isLoading}
          error={!!fieldErrors.email}
        />
        <FormError message={fieldErrors.email} />
      </div>

      <div>
        <FieldLabel>Пароль</FieldLabel>
        <div className="relative">
          <AppInput
            id="password"
            type={showPassword ? 'text' : 'password'}
            required
            value={formData.password}
            onChange={handleChange}
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

      <div>
        <FieldLabel>Подтвердите пароль</FieldLabel>
        <div className="relative">
          <AppInput
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            required
            value={formData.confirmPassword}
            onChange={handleChange}
            disabled={isLoading}
            error={!!fieldErrors.confirmPassword}
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
        <FormError message={fieldErrors.confirmPassword} />
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="flex h-[52px] w-full items-center justify-center rounded-2xl bg-primary text-[15px] font-semibold text-white shadow-[0_4px_16px_rgba(37,99,235,0.28)] transition-all disabled:opacity-60"
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Зарегистрироваться
      </button>
    </AuthForm>
  );
};
