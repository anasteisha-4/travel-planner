import { AuthForm, Button, Input, Label } from '@/shared/ui';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useLogin } from '../model/useLogin';

const FieldError = ({ message }: { message?: string }) => {
  if (!message) return null;
  return (
    <p className="text-[13px] text-destructive font-medium mt-1.5 animate-in fade-in-0 slide-in-from-top-1 duration-200">
      {message}
    </p>
  );
};

export const LoginForm = ({ 
  oauthCallback = false,
  onSuccess,
  onRegisterClick,
  onError
}: { 
  oauthCallback?: boolean;
  onSuccess: (onboardingCompleted?: boolean) => void;
  onRegisterClick: () => void;
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
      title="Triply — персональный планировщик поездок"
      description="Войдите, чтобы продолжить"
      onSubmit={handleSubmit}
      onYandexLogin={handleYandexLogin}
      footerText="Нет аккаунта?"
      footerLinkText="Зарегистрироваться"
      onFooterLinkClick={onRegisterClick}
      isLoading={isLoading}
    >
      <div className="space-y-1">
        <Label htmlFor="identifier">Логин или почта</Label>
        <Input 
          id="identifier" 
          type="text" 
          placeholder="email@example.com" 
          required 
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          disabled={isLoading}
          className={fieldErrors.identifier ? 'border-destructive focus-visible:ring-destructive' : ''}
        />
        <FieldError message={fieldErrors.identifier} />
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Пароль</Label>
          <Button 
            variant="link"
            type="button"
            onClick={(e) => { e.preventDefault(); }}
            className="text-sm p-0 h-auto"
          >
            Забыли пароль?
          </Button>
        </div>
        <div className="relative">
          <Input 
            id="password" 
            type={showPassword ? "text" : "password"} 
            required 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            className={`pr-10 ${fieldErrors.password ? 'border-destructive focus-visible:ring-destructive' : ''}`}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground active:text-foreground transition-colors"
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>
        <FieldError message={fieldErrors.password} />
      </div>
      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Войти
      </Button>
    </AuthForm>
  );
};
