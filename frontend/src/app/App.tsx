import { DashboardPage } from '@/pages/dashboard';
import { LoginPage, OAuthCallbackPage } from '@/pages/login';
import { OnboardingPage } from '@/pages/onboarding';
import { RegisterPage } from '@/pages/register';
import { ThemeProvider } from '@/shared/ui';
import { BottomNav } from '@/widgets/bottom-nav';
import { Layout } from '@/widgets/layout';
import { useEffect } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes, useNavigate } from 'react-router-dom';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  return token ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

const AppEffects = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleLogout = () => navigate('/login', { replace: true });
    window.addEventListener('auth:logout', handleLogout);

    if (window.matchMedia('(display-mode: standalone)').matches || 'standalone' in window.navigator &&
      window.navigator.standalone === true) {
      document.body.classList.add('pwa-standalone');
    }

    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [navigate]);

  return null;
}

export const App = () => {
  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <Router>
        <AppEffects />
        <Routes>
          <Route element={<Layout bottomNav={<BottomNav />} />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route 
              path="/login" 
              element={
                <PublicOnlyRoute>
                  <LoginPage />
                </PublicOnlyRoute>
              } 
            />
            <Route 
              path="/register" 
              element={
                <PublicOnlyRoute>
                  <RegisterPage />
                </PublicOnlyRoute>
              } 
            />
            <Route 
              path="/onboarding" 
              element={
                <PrivateRoute>
                  <OnboardingPage />
                </PrivateRoute>
              } 
            />
            <Route 
              path="/dashboard" 
              element={
                <PrivateRoute>
                  <DashboardPage />
                </PrivateRoute>
              } 
            />

            <Route path="/auth/yandex/callback" element={<OAuthCallbackPage />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}
