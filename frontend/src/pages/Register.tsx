import { authAPI } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    login: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.id]: e.target.value }));
  };

  const validatePassword = (password: string) => {
    if (password.length < 8) return 'Пароль должен быть не менее 8 символов';
    if (!/[a-zа-яё]/i.test(password.toLowerCase()) || !/[A-ZА-ЯЁ]/.test(password)) return 'Пароль должен содержать строчные и заглавные буквы';
    if (!/\d/.test(password)) return 'Пароль должен содержать цифры';
    if (!/[^a-zA-Zа-яА-ЯёЁ0-9\s]/.test(password)) return 'Пароль должен содержать специальные символы';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast({
        variant: 'destructive',
        title: 'Ошибка валидации',
        description: 'Пароли не совпадают'
      });
      return;
    }

    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      toast({
        variant: 'destructive',
        title: 'Слишком простой пароль',
        description: passwordError
      });
      return;
    }

    setIsLoading(true);
    try {

      const registerData = {
        email: formData.email,
        login: formData.login,
        password: formData.password
      };
      const res = await authAPI.register(registerData);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      navigate('/onboarding');
    } catch (e: unknown) {
      const error = e as { response?: { data?: { detail?: string | Array<{msg: string; loc: string[]}> } } };
      let message = 'Произошла ошибка при регистрации';
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map(d => d.msg).join('. ');
      }
      toast({ 
        variant: 'destructive', 
        title: 'Ошибка регистрации', 
        description: message 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleYandexLogin = () => {
    const origin = window.location.origin;
    window.location.href = authAPI.getYandexAuthUrl(origin);
  };

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-md mx-auto glass-card">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center justify-center">
            <img src="/assets/logo.png" alt="Triply Logo" className="h-20 w-20 object-contain drop-shadow-md" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Присоединяйтесь к Triply</CardTitle>
          <CardDescription>
            Создайте аккаунт и начните планировать путешествия
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login">Логин<span className="text-destructive ml-1">*</span></Label>
              <Input id="login" type="text" required value={formData.login} onChange={handleChange} disabled={isLoading} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Почта<span className="text-destructive ml-1">*</span></Label>
              <Input id="email" type="email" placeholder="email@example.com" required value={formData.email} onChange={handleChange} disabled={isLoading} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Пароль<span className="text-destructive ml-1">*</span></Label>
              <Input 
                id="password" 
                type="password" 
                required 
                value={formData.password} 
                onChange={handleChange} 
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Подтвердите пароль<span className="text-destructive ml-1">*</span></Label>
              <Input 
                id="confirmPassword" 
                type="password" 
                required 
                value={formData.confirmPassword} 
                onChange={handleChange} 
                disabled={isLoading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Зарегистрироваться
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
            Уже есть аккаунт?{' '}
            <Button 
              variant="link"
              type="button"
              onClick={(e) => { e.preventDefault(); navigate('/login'); }} 
              className="text-primary font-medium text-base p-0 h-auto"
            >
              Войти
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
