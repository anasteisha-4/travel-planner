import { AuthForm, Button, Input, Label } from '@/shared/ui';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useRegister } from '../model/useRegister';

const FieldError = ({ message }: { message?: string }) => {
  if (!message) return null;
  return (
    <p className="text-[13px] text-destructive font-medium mt-1.5 animate-in fade-in-0 slide-in-from-top-1 duration-200">
      {message}
    </p>
  );
};

export const RegisterForm = ({
  onSuccess,
  onLoginClick
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
      title="Присоединяйтесь к Triply"
      description="Создайте аккаунт и начните планировать путешествия"
      onSubmit={handleSubmit}
      onYandexLogin={handleYandexLogin}
      footerText="Уже есть аккаунт?"
      footerLinkText="Войти"
      onFooterLinkClick={onLoginClick}
      isLoading={isLoading}
    >
      <div className="space-y-1">
        <Label htmlFor="login">Логин<span className="text-destructive ml-1">*</span></Label>
        <Input
          id="login"
          type="text"
          required
          value={formData.login}
          onChange={handleChange}
          disabled={isLoading}
          className={fieldErrors.login ? 'border-destructive focus-visible:ring-destructive' : ''}
        />
        <FieldError message={fieldErrors.login} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="email">Почта<span className="text-destructive ml-1">*</span></Label>
        <Input
          id="email"
          type="email"
          placeholder="email@example.com"
          required
          value={formData.email}
          onChange={handleChange}
          disabled={isLoading}
          className={fieldErrors.email ? 'border-destructive focus-visible:ring-destructive' : ''}
        />
        <FieldError message={fieldErrors.email} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="password">Пароль<span className="text-destructive ml-1">*</span></Label>
        <div className="relative">
          <Input 
            id="password" 
            type={showPassword ? "text" : "password"} 
            required 
            value={formData.password} 
            onChange={handleChange} 
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
      <div className="space-y-1">
        <Label htmlFor="confirmPassword">Подтвердите пароль<span className="text-destructive ml-1">*</span></Label>
        <div className="relative">
          <Input 
            id="confirmPassword" 
            type={showPassword ? "text" : "password"} 
            required 
            value={formData.confirmPassword} 
            onChange={handleChange} 
            disabled={isLoading}
            className={`pr-10 ${fieldErrors.confirmPassword ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
        <FieldError message={fieldErrors.confirmPassword} />
      </div>
      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Зарегистрироваться
      </Button>
    </AuthForm>
  );
};
