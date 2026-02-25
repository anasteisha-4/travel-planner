import { authAPI } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { Calendar, LogOut, Mail, MapPin, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

type UserProfile = {
  login?: string;
  email?: string;
  yandex_id?: string;
  onboarding_completed?: boolean;
};

export const Dashboard = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login', { replace: true });
  };

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await authAPI.getProfile();
        if (data.onboarding_completed === false) {
          navigate('/onboarding', { replace: true });
          return;
        }
        setProfile(data);
      } catch {
        toast({ variant: 'destructive', title: 'Ошибка', description: 'Не удалось загрузить данные профиля' });
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [toast, navigate]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-12 w-12 bg-primary/20 rounded-full mb-4"></div>
          <div className="h-4 w-32 bg-primary/20 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 max-w-4xl mx-auto w-full animate-in fade-in-50 duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Главная</h1>
        <div className="flex gap-2">
          <Button 
            variant="ghost" 
            onClick={handleLogout} 
            className="text-destructive hover:bg-destructive/10 hover:text-destructive px-2 md:px-4"
          >
            <LogOut className="h-5 w-5 md:mr-2" />
            <span className="hidden md:inline">Выйти</span>
          </Button>
        </div>
      </div>
      
      <Separator />
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2">
              <User className="h-5 w-5 text-primary" /> Профиль
            </CardTitle>
            <CardDescription>Ваши данные</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 flex flex-col">
            <div className="flex justify-between border-b pb-2">
              <span className="text-muted-foreground font-medium text-sm">Логин</span>
              <span className="font-semibold text-primary">{profile?.login}</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="text-muted-foreground font-medium text-sm flex items-center gap-2">
                <Mail className="h-4 w-4" /> Email
              </span>
              <span>{profile?.email}</span>
            </div>

          </CardContent>
        </Card>
        
        <div className="space-y-6">
          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <MapPin className="h-5 w-5 text-primary" /> Ближайшие поездки
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-6 text-muted-foreground">
                <Calendar className="mr-2 h-10 w-10 mx-auto mb-3 opacity-50" />
                <p>Поездок пока нет</p>
                <Button className="mt-4" size="sm">Спланировать первую поездку</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
