import { ResetPasswordForm } from '@/features/auth';
import { useNavigate } from 'react-router-dom';

export const ResetPasswordPage = () => {
  const navigate = useNavigate();

  return (
    <ResetPasswordForm
      onLoginClick={() => navigate('/login')}
    />
  );
};
