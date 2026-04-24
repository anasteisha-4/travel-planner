import { LoginForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const LoginPage = () => {
  const navigate = useNavigate();

  const handleSuccess = () => {
    navigate('/onboarding');
  };

  return (
    <LoginForm
      onSuccess={handleSuccess}
      onRegisterClick={() => navigate('/register')}
      onForgotPasswordClick={() => navigate('/forgot-password')}
    />
  );
};
