import { LoginForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const OAuthCallbackPage = () => {
  const navigate = useNavigate();

  const handleSuccess = () => {
    navigate('/onboarding', { replace: true });
  };

  return (
    <LoginForm
      oauthCallback={true}
      onSuccess={handleSuccess}
      onRegisterClick={() => navigate('/register')}
      onForgotPasswordClick={() => navigate('/forgot-password')}
      onError={() => navigate('/login', { replace: true })}
    />
  );
};
