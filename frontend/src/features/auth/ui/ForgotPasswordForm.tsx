import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from '@/shared/ui';
import { ArrowLeft, Loader2, MailCheck } from 'lucide-react';
import { useForgotPassword } from '../model/useForgotPassword';

const FieldError = ({ message }: { message?: string }) => {
  if (!message) return null;
  return (
    <p className="mt-1.5 text-[13px] font-medium text-destructive duration-200 animate-in fade-in-0 slide-in-from-top-1">
      {message}
    </p>
  );
};

export const ForgotPasswordForm = ({ onBackToLogin }: { onBackToLogin: () => void }) => {
  const { email, setEmail, isLoading, isSent, fieldErrors, handleSubmit } = useForgotPassword();

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="glass-card mx-auto w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center justify-center">
            <img
              src="/assets/logo.png"
              alt="Triply Logo"
              className="h-20 w-20 object-contain drop-shadow-md"
            />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            {isSent ? 'Проверьте почту' : 'Сброс пароля'}
          </CardTitle>
          <CardDescription>
            {isSent
              ? 'Мы отправили письмо с инструкциями для сброса пароля'
              : 'Введите вашу почту, и мы отправим ссылку для сброса пароля'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isSent ? (
            <div className="flex flex-col items-center space-y-6 py-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <MailCheck className="h-8 w-8 text-primary" />
              </div>
              <p className="text-center text-sm leading-relaxed text-muted-foreground">
                Если аккаунт с адресом <strong className="text-foreground">{email}</strong>{' '}
                существует, вы получите письмо со ссылкой для сброса пароля. Ссылка действительна 20
                минут.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1">
                <Label htmlFor="email">Почта</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="email@example.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className={
                    fieldErrors.email ? 'border-destructive focus-visible:ring-destructive' : ''
                  }
                />
                <FieldError message={fieldErrors.email} />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Отправить ссылку
              </Button>
            </form>
          )}
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button
            variant="ghost"
            type="button"
            onClick={onBackToLogin}
            className="w-full text-muted-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Вернуться к входу
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
