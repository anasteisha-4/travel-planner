import { userApi } from '@/entities/user';
import { useToast } from '@/shared/ui';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { z } from 'zod';
import { authApi } from '../index';
import { AuthCredentialsSchema } from './types';

type FieldErrors = Record<string, string>;

export const useLogin = ({
  oauthCallback = false,
  onSuccess,
  onError,
}: {
  oauthCallback?: boolean;
  onSuccess: (onboardingCompleted?: boolean) => void;
  onError?: () => void;
}) => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  
  const location = useLocation();
  const { toast } = useToast();

  useEffect(() => {
    const processOAuth = async () => {
      if (oauthCallback) {
        setIsLoading(true);
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        
        if (code) {
          try {
            const res = await authApi.yandexCallback({ 
              code,
              redirect_uri: `${window.location.origin}/auth/yandex/callback`
            });
            localStorage.setItem('access_token', res.access_token);
            localStorage.setItem('refresh_token', res.refresh_token);
            const profile = await userApi.getProfile();
            onSuccess(profile.onboarding_completed);
          } catch (e: unknown) {
            let message = 'Не удалось авторизоваться через Яндекс';
            if (axios.isAxiosError(e)) {
              message = e.response?.data?.detail || message;
            }
            toast({ 
              variant: 'destructive', 
              title: 'Ошибка OAuth', 
              description: message 
            });
            if (onError) onError();
          }
        } else {
          toast({ variant: 'destructive', title: 'Ошибка', description: 'Яндекс не вернул код авторизации' });
          if (onError) onError();
        }
        setIsLoading(false);
      }
    };
    
    processOAuth();
  }, [oauthCallback, location, onError, onSuccess, toast]);

  const handleFieldChange = (field: string, value: string) => {
    if (field === 'identifier') setIdentifier(value);
    if (field === 'password') setPassword(value);
    if (fieldErrors[field]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    setIsLoading(true);

    try {
      const parsedData = AuthCredentialsSchema.parse({ identifier, password });
      const res = await authApi.login(parsedData);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      const profile = await userApi.getProfile();
      onSuccess(profile.onboarding_completed);
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
          description: err.response?.data?.detail || 'Неверный логин/пароль' 
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
    identifier,
    setIdentifier: (v: string) => handleFieldChange('identifier', v),
    password,
    setPassword: (v: string) => handleFieldChange('password', v),
    showPassword,
    setShowPassword,
    isLoading,
    fieldErrors,
    handleSubmit,
    handleYandexLogin,
  };
};
