import { useEffect } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes, useNavigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ThemeProvider } from './components/ThemeProvider';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { Onboarding } from './pages/Onboarding';
import { Register } from './pages/Register';

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


    const isStandalone = 
      window.matchMedia('(display-mode: standalone)').matches || 
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window.navigator as any).standalone === true;

    if (isStandalone) {
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
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route 
              path="/login" 
              element={
                <PublicOnlyRoute>
                  <Login />
                </PublicOnlyRoute>
              } 
            />
            <Route 
              path="/register" 
              element={
                <PublicOnlyRoute>
                  <Register />
                </PublicOnlyRoute>
              } 
            />
            <Route 
              path="/onboarding" 
              element={
                <PrivateRoute>
                  <Onboarding />
                </PrivateRoute>
              } 
            />
            <Route 
              path="/dashboard" 
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              } 
            />

            <Route path="/auth/yandex/callback" element={<Login oauthCallback />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}
