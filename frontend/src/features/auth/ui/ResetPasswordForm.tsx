import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, Input, Label } from '@/shared/ui';
import { ArrowLeft, CheckCircle2, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useResetPassword } from '../model/useResetPassword';

const FieldError = ({ message }: { message?: string }) => {
  if (!message) return null;
  return (
    <p className="text-[13px] text-destructive font-medium mt-1.5 animate-in fade-in-0 slide-in-from-top-1 duration-200">
      {message}
    </p>
  );
};

export const ResetPasswordForm = ({
  onLoginClick,
}: {
  onLoginClick: () => void;
}) => {
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
      <div className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md mx-auto glass-card">
          <CardHeader className="space-y-3 text-center">
            <CardTitle className="text-2xl font-bold tracking-tight">Недействительная ссылка</CardTitle>
            <CardDescription>
              Ссылка для сброса пароля недействительна или истекла. Запросите новую ссылку.
            </CardDescription>
          </CardHeader>
          <CardFooter className="flex flex-col space-y-4">
            <Button onClick={onLoginClick} className="w-full">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Вернуться к входу
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-md mx-auto glass-card">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center justify-center">
            <img src="/assets/logo.png" alt="Triply Logo" className="h-20 w-20 object-contain drop-shadow-md" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            {isSuccess ? 'Пароль обновлён' : 'Новый пароль'}
          </CardTitle>
          <CardDescription>
            {isSuccess
              ? 'Ваш пароль успешно изменён'
              : 'Придумайте новый пароль для вашего аккаунта'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isSuccess ? (
            <div className="flex flex-col items-center space-y-6 py-4">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10">
                <CheckCircle2 className="h-8 w-8 text-green-500" />
              </div>
              <p className="text-sm text-muted-foreground text-center leading-relaxed">
                Можете войти в аккаунт с новым паролем.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1">
                <Label htmlFor="new_password">Новый пароль<span className="text-destructive ml-1">*</span></Label>
                <div className="relative">
                  <Input
                    id="new_password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={isLoading}
                    className={`pr-10 ${fieldErrors.new_password ? 'border-destructive focus-visible:ring-destructive' : ''}`}
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
                <FieldError message={fieldErrors.new_password} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="confirm_password">Подтвердите пароль<span className="text-destructive ml-1">*</span></Label>
                <Input
                  id="confirm_password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                  className={fieldErrors.confirm_password ? 'border-destructive focus-visible:ring-destructive' : ''}
                />
                <FieldError message={fieldErrors.confirm_password} />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Сбросить пароль
              </Button>
            </form>
          )}
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button
            variant="ghost"
            type="button"
            onClick={onLoginClick}
            className="w-full text-muted-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {isSuccess ? 'Войти' : 'Вернуться к входу'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
