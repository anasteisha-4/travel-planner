import { OnboardingWizard } from '@/features/onboarding';
import { useNavigate } from 'react-router-dom';

export const OnboardingPage = () => {
  const navigate = useNavigate();

  const handleComplete = () => {
    navigate('/dashboard', { replace: true });
  };

  return <OnboardingWizard onComplete={handleComplete} onSkip={handleComplete} />;
};
