import { authAPI } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const Login = ({ oauthCallback = false }: { oauthCallback?: boolean }) => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();

  useEffect(() => {

    const processOAuth = async () => {
      if (oauthCallback) {
        setIsLoading(true);
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        
        if (code) {
          try {
            const res = await authAPI.yandexCallback({ 
              code,
              redirect_uri: `${window.location.origin}/auth/yandex/callback`
            });
            localStorage.setItem('access_token', res.access_token);
            localStorage.setItem('refresh_token', res.refresh_token);
            const profile = await authAPI.getProfile();
            window.location.replace(profile.onboarding_completed ? '/dashboard' : '/onboarding');
          } catch (e: unknown) {
            const error = e as { response?: { data?: { detail?: string } } };
            toast({ 
              variant: 'destructive', 
              title: 'Ошибка OAuth', 
              description: error.response?.data?.detail || 'Не удалось авторизоваться через Яндекс' 
            });
            navigate('/login');
          }
        } else {
          toast({ variant: 'destructive', title: 'Ошибка', description: 'Яндекс не вернул код авторизации' });
          navigate('/login');
        }
        setIsLoading(false);
      }
    };
    
    processOAuth();
  }, [oauthCallback, location, navigate, toast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await authAPI.login({ identifier, password });
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      const profile = await authAPI.getProfile();
      navigate(profile.onboarding_completed ? '/dashboard' : '/onboarding');
    } catch {
      toast({ 
        variant: 'destructive', 
        title: 'Ошибка входа', 
        description: 'Неверный логин/пароль' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleYandexLogin = () => {
    const origin = window.location.origin;
    window.location.href = authAPI.getYandexAuthUrl(origin);
  };

  if (oauthCallback) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center">
      <Card className="w-full max-w-md mx-auto glass-card">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center justify-center">
            <img src="/assets/logo.png" alt="Triply Logo" className="h-20 w-20 object-contain drop-shadow-md" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Triply — персональный планировщик поездок</CardTitle>
          <CardDescription>
            Войдите, чтобы продолжить
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="identifier">Логин или почта</Label>
              <Input 
                id="identifier" 
                type="text" 
                placeholder="email@example.com" 
                required 
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Пароль</Label>
                <Button 
                  variant="link"
                  type="button"
                  onClick={(e) => { e.preventDefault(); /* TODO: Forgot password */ }} 
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
                  className="pr-10"
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
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Войти
            </Button>
          </form>
          
            <div className="my-6 flex items-center">
              <Separator className="flex-1 opacity-50" />
              <span className="mx-4 text-xs text-muted-foreground uppercase tracking-wider font-semibold">Или продолжить через</span>
              <Separator className="flex-1 opacity-50" />
            </div>
            
            <Button 
              type="button"
              variant="outline" 
              className="w-full bg-[#FC3F1D]/10 active:bg-[#FC3F1D]/20 text-[#FC3F1D] border-[#FC3F1D]/20 transition-all group backdrop-blur-sm" 
              onClick={handleYandexLogin}
              disabled={isLoading}
            >
                <img src="/assets/yandex.png" alt="Yandex" className="h-4 w-4 object-contain" />
                Яндекс ID
            </Button>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <div className="text-center text-sm text-muted-foreground">
            Нет аккаунта?{' '}
            <Button 
              variant="link"
              type="button"
              onClick={(e) => { e.preventDefault(); navigate('/register'); }} 
              className="text-primary font-medium text-base p-0 h-auto"
            >
              Зарегистрироваться
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
