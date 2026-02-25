import { LoginForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const OAuthCallbackPage = () => {
  const navigate = useNavigate();

  const handleSuccess = (onboardingCompleted?: boolean) => {
    navigate(onboardingCompleted ? '/dashboard' : '/onboarding', { replace: true });
  };

  return (
    <LoginForm 
      oauthCallback={true} 
      onSuccess={handleSuccess}
      onRegisterClick={() => navigate('/register')}
      onError={() => navigate('/login', { replace: true })}
    />
  );
};
