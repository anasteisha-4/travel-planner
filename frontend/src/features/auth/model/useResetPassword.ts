import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { authApi } from '../api/auth.api';
import { ResetPasswordSchema } from './types';

type FieldErrors = Record<string, string>;

export const useResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const { toast } = useToast();

  const handleFieldChange = (field: string, value: string) => {
    if (field === 'new_password') setNewPassword(value);
    if (field === 'confirm_password') setConfirmPassword(value);
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});

    if (!token) {
      toast({
        variant: 'destructive',
        title: 'Ошибка',
        description: 'Ссылка для сброса пароля недействительна',
      });
      return;
    }

    setIsLoading(true);

    try {
      ResetPasswordSchema.parse({ new_password: newPassword, confirm_password: confirmPassword });
      await authApi.resetPassword({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setIsSuccess(true);
    } catch (err) {
      if (err instanceof z.ZodError) {
        const errors: FieldErrors = {};
        err.issues.forEach((issue) => {
          const field = issue.path[0];
          if (typeof field === 'string' && !errors[field]) {
            errors[field] = issue.message;
          }
        });
        setFieldErrors(errors);
      } else if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        let message = 'Не удалось сбросить пароль';
        if (typeof detail === 'string') {
          if (detail.includes('differ from the current')) {
            message = 'Новый пароль не должен совпадать с текущим';
          } else if (detail.includes('expired') || detail.includes('Invalid')) {
            message = 'Ссылка для сброса пароля истекла или уже использована';
          } else {
            message = detail;
          }
        }
        toast({
          variant: 'destructive',
          title: 'Ошибка',
          description: message,
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return {
    token,
    newPassword,
    confirmPassword,
    showPassword,
    setShowPassword,
    setNewPassword: (v: string) => handleFieldChange('new_password', v),
    setConfirmPassword: (v: string) => handleFieldChange('confirm_password', v),
    isLoading,
    isSuccess,
    fieldErrors,
    handleSubmit,
  };
};
