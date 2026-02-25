import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useState } from 'react';
import { z } from 'zod';
import { authApi } from '../api/auth.api';
import { ForgotPasswordSchema } from './types';

type FieldErrors = Record<string, string>;

export const useForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const { toast } = useToast();

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (fieldErrors.email) {
      setFieldErrors({});
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    setIsLoading(true);

    try {
      ForgotPasswordSchema.parse({ email });
      await authApi.forgotPassword(email);
      setIsSent(true);
    } catch (err) {
      if (err instanceof z.ZodError) {
        const errors: FieldErrors = {};
        err.issues.forEach(issue => {
          const field = issue.path[0];
          if (typeof field === 'string') {
            errors[field] = issue.message;
          }
        });
        setFieldErrors(errors);
      } else if (axios.isAxiosError(err)) {
        toast({
          variant: 'destructive',
          title: 'Ошибка',
          description: err.response?.data?.detail || 'Не удалось отправить запрос',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return {
    email,
    setEmail: handleEmailChange,
    isLoading,
    isSent,
    fieldErrors,
    handleSubmit,
  };
};
