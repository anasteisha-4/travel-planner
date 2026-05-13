import { queryClient } from '@/shared/lib/query-client';
import { sendEvent } from '@/shared/api';
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
  onSuccess: () => void;
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
            sendEvent('login_started', { provider: 'yandex', flow: 'oauth_callback' });
            const res = await authApi.yandexCallback({
              code,
              redirect_uri: `${window.location.origin}/auth/yandex/callback`,
            });
            localStorage.setItem('access_token', res.access_token);
            localStorage.setItem('refresh_token', res.refresh_token);
            queryClient.clear();
            sendEvent('login_succeeded', { provider: 'yandex', flow: 'oauth_callback' });
            onSuccess();
          } catch (e: unknown) {
            let message = 'Не удалось авторизоваться через Яндекс';
            if (axios.isAxiosError(e)) {
              message = e.response?.data?.detail || message;
            }
            toast({
              variant: 'destructive',
              title: 'Ошибка авторизации',
              description: message,
            });
            sendEvent('login_failed', { provider: 'yandex', flow: 'oauth_callback', reason_code: 'oauth_callback_failed' });
            if (onError) onError();
          }
        } else {
          toast({
            variant: 'destructive',
            title: 'Ошибка',
            description: 'Яндекс не вернул код авторизации',
          });
          sendEvent('login_failed', { provider: 'yandex', flow: 'oauth_callback', reason_code: 'missing_oauth_code' });
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
    setIsLoading(true);
    sendEvent('login_started', { provider: 'password', flow: 'login' });

    try {
      const parsedData = AuthCredentialsSchema.parse({ identifier, password });
      const res = await authApi.login(parsedData);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      queryClient.clear();
      sendEvent('login_succeeded', { provider: 'password', flow: 'login' });
      onSuccess();
    } catch (err) {
      if (err instanceof z.ZodError) {
        const errors: FieldErrors = {};
        err.issues.forEach((issue) => {
          const field = issue.path[0];
          if (typeof field === 'string') {
            errors[field] = issue.message;
          }
        });
        setFieldErrors(errors);
        sendEvent('login_failed', { provider: 'password', flow: 'login', reason_code: 'validation_error' });
      } else if (axios.isAxiosError(err)) {
        toast({
          variant: 'destructive',
          title: 'Ошибка',
          description: err.response?.data?.detail || 'Неверный логин/пароль',
        });
        sendEvent('login_failed', { provider: 'password', flow: 'login', reason_code: `http_${err.response?.status ?? 'network'}` });
      } else {
        sendEvent('login_failed', { provider: 'password', flow: 'login', reason_code: 'unknown_error' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleYandexLogin = () => {
    const origin = window.location.origin;
    sendEvent('login_started', { provider: 'yandex', flow: 'oauth_redirect' });
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
