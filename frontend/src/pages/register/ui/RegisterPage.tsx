import { RegisterForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const RegisterPage = () => {
  const navigate = useNavigate();

  return (
    <RegisterForm 
      onSuccess={() => navigate('/onboarding')} 
      onLoginClick={() => navigate('/login')} 
    />
  );
};
