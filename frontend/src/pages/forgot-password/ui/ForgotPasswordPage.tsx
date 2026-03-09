import { ForgotPasswordForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const ForgotPasswordPage = () => {
  const navigate = useNavigate();

  return <ForgotPasswordForm onBackToLogin={() => navigate('/login')} />;
};
