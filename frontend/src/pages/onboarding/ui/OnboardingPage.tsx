import { OnboardingV2Wizard } from '@/features/onboarding-v2';
import { profileApi } from '@/features/profile';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const OnboardingPage = () => {
  const navigate = useNavigate();

  const { data: tripProfile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: profileApi.getProfile,
    staleTime: 1000 * 60 * 5,
  });

  useEffect(() => {
    if (!isLoading && tripProfile?.onboarding_completed) {
      navigate('/recommendations', { replace: true });
    }
  }, [isLoading, tripProfile, navigate]);

  const handleComplete = () => {
    navigate('/recommendations', { replace: true });
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-stone-300" />
      </div>
    );
  }

  if (tripProfile?.onboarding_completed) {
    return null;
  }

  return <OnboardingV2Wizard onComplete={handleComplete} />;
};
