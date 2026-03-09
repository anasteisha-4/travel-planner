import { useProfile } from '@/entities/user';
import { LogoutButton, authApi } from '@/features/auth';
import { PreferencesEditor, PreferencesView, usePreferences } from '@/features/profile';
import { useIsOnline } from '@/shared/lib';
import { Button, Card, CardContent, PageHeader, Separator, useToast } from '@/shared/ui';
import { ClipboardList, Edit, Loader2, Settings, User } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const isOnline = useIsOnline();
  const { toast } = useToast();

  const handleUnauthenticated = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login', { replace: true });
    } else {
      navigate('/onboarding', { replace: true });
    }
  }, [navigate]);

  const { profile, loading } = useProfile(handleUnauthenticated);
  const { preferences, hasPreferences, isFetching, refetch } = usePreferences();

  const handleLogout = useCallback(async () => {
    if (!isOnline) {
      toast({
        variant: 'destructive',
        title: 'Офлайн',
        description: 'Нет интернета',
      });
      return;
    }
    await authApi.logout();
    navigate('/login', { replace: true });
  }, [navigate, isOnline, toast]);

  const handleSaved = () => {
    refetch();
    setIsEditing(false);
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="mb-4 h-12 w-12 rounded-full bg-primary/20" />
          <div className="h-4 w-32 rounded bg-primary/20" />
        </div>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 pb-20">
      <PageHeader className="justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Профиль</h1>
        <LogoutButton onLogout={handleLogout} />
      </PageHeader>

      <div className="flex items-center gap-2">
        <User className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-semibold">Данные</h2>
      </div>
      <Card>
        <CardContent className="space-y-4">
          <div className="flex justify-between border-b pb-2">
            <span className="text-sm font-medium text-muted-foreground">Логин</span>
            <span className="font-semibold text-primary">{profile.login}</span>
          </div>
          <div className="flex justify-between pt-2">
            <span className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              Почта
            </span>
            <span>{profile.email}</span>
          </div>
        </CardContent>
      </Card>

      <Separator />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Предпочтения</h2>
        </div>
        {hasPreferences && (
          <Button
            variant="ghost"
            size="sm"
            className="h-10 text-primary"
            disabled={!isOnline}
            onClick={() => setIsEditing(true)}
          >
            <Edit className="mr-1.5 h-4 w-4" />
          </Button>
        )}
      </div>

      {isFetching ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : hasPreferences ? (
        <PreferencesView preferences={preferences} />
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center gap-4 py-8">
            <ClipboardList className="h-10 w-10 text-muted-foreground/50" />
            <p className="text-center text-sm text-muted-foreground">
              Анкета предпочтений ещё не заполнена
            </p>
            <Button onClick={() => setIsEditing(true)} className="h-11" disabled={!isOnline}>
              Указать предпочтения
            </Button>
          </CardContent>
        </Card>
      )}

      <PreferencesEditor
        open={isEditing}
        onOpenChange={setIsEditing}
        initialData={preferences}
        onSaved={handleSaved}
      />
    </div>
  );
};
