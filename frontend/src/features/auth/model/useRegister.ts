import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useState } from 'react';
import { z } from 'zod';
import { authApi } from '../api/auth.api';
import { RegisterFormSchema } from './types';
type FieldErrors = Record<string, string>;

export const useRegister = ({ onSuccess }: { onSuccess: () => void }) => {
  const [formData, setFormData] = useState({
    email: '',
    login: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const { toast } = useToast();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
    if (fieldErrors[id]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});

    setIsLoading(true);
    try {
      const parsedData = RegisterFormSchema.parse(formData);
      
      // Separate API data from validation data
      const { confirmPassword: _, ...apiData } = parsedData;
      
      const res = await authApi.register(apiData);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      onSuccess();
    } catch (err) {
      if (err instanceof z.ZodError) {
        const errors: FieldErrors = {};
        // Use a map to keep only the first error for each field
        err.issues.forEach(issue => {
          const field = issue.path[0] as string;
          if (!errors[field]) {
            errors[field] = issue.message;
          }
        });
        setFieldErrors(errors);
      } else if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        let message = 'Произошла ошибка при регистрации';
        if (typeof detail === 'string') {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail.map((d: { msg: string }) => d.msg).join('. ');
        }
        toast({ 
          variant: 'destructive', 
          title: 'Ошибка регистрации', 
          description: message 
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleYandexLogin = () => {
    const origin = window.location.origin;
    window.location.href = authApi.getYandexAuthUrl(origin);
  };

  return {
    formData,
    handleChange,
    fieldErrors,
    isLoading,
    showPassword,
    setShowPassword,
    handleSubmit,
    handleYandexLogin,
  };
};
