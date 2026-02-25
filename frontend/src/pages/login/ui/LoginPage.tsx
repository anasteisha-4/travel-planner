import { LoginForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const LoginPage = () => {
  const navigate = useNavigate();

  const handleSuccess = (onboardingCompleted?: boolean) => {
    navigate(onboardingCompleted ? '/dashboard' : '/onboarding');
  };

  return (
    <LoginForm 
      onSuccess={handleSuccess} 
      onRegisterClick={() => navigate('/register')} 
    />
  );
};
