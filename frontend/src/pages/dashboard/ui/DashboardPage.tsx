import { ProfileCard, useProfile } from '@/entities/user';
import { LogoutButton, authApi } from '@/features/auth';
import { TripsPreview } from '@/features/trips';
import { Separator } from '@/shared/ui';
import { useNavigate } from 'react-router-dom';

export const DashboardPage = () => {
  const navigate = useNavigate();

  const handleUnauthenticated = () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login', { replace: true });
    } else {
      navigate('/onboarding', { replace: true });
    }
  };

  const { profile, loading } = useProfile(handleUnauthenticated);

  const handleLogout = async () => {
    await authApi.logout();
    navigate('/login', { replace: true });
  };

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

  // Double-checking profile exists since handleUnauthenticated might just be redirecting
  if (!profile) return null;

  return (
    <div className="flex-1 space-y-6 max-w-4xl mx-auto w-full p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Главная</h1>
        <div className="flex gap-2">
          <LogoutButton onLogout={handleLogout} />
        </div>
      </div>
      
      <Separator />
      
      <div className="grid gap-6 md:grid-cols-2">
        <ProfileCard profile={profile} />
        <TripsPreview />
      </div>
    </div>
  );
};
