import { DashboardPage } from '@/pages/dashboard';
import { RecommendationsPage } from '@/pages/recommendations';
import { ForgotPasswordPage } from '@/pages/forgot-password';
import { LoginPage, OAuthCallbackPage } from '@/pages/login';
import { OnboardingPage } from '@/pages/onboarding';
import { ProfilePage } from '@/pages/profile';
import { RegisterPage } from '@/pages/register';
import { ResetPasswordPage } from '@/pages/reset-password';
import { TripCreatePage } from '@/pages/trip-create';
import { TripAnalyticsTab, TripDetailPage, TripDiaryTab, TripExpensesTab, TripInfoTab, TripItineraryTab } from '@/pages/trip-detail';
import { TripsPage } from '@/pages/trips';
import { sendAppOpened, sendPageViewed, sendSessionEnded, sendSessionStarted } from '@/shared/api';
import { queryClient } from '@/shared/lib';
import { ThemeProvider } from '@/shared/ui';
import { BottomNav } from '@/widgets/bottom-nav';
import { Layout } from '@/widgets/layout';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useEffect } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes, useLocation, useNavigate } from 'react-router-dom';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  return token ? <>{children}</> : <Navigate to="/login" replace />;
};

const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  return token ? <Navigate to="/dashboard" replace /> : <>{children}</>;
};

const AppEffects = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const handleLogout = () => navigate('/login', { replace: true });
    const handlePageHide = () => sendSessionEnded();
    window.addEventListener('auth:logout', handleLogout);
    window.addEventListener('pagehide', handlePageHide);

    sendAppOpened();
    sendSessionStarted();

    if (
      window.matchMedia('(display-mode: standalone)').matches ||
      ('standalone' in window.navigator && window.navigator.standalone === true)
    ) {
      document.body.classList.add('pwa-standalone');
    }

    return () => {
      window.removeEventListener('auth:logout', handleLogout);
      window.removeEventListener('pagehide', handlePageHide);
    };
  }, [navigate]);

  useEffect(() => {
    sendPageViewed(`${location.pathname}${location.search}`);
  }, [location.pathname, location.search]);

  return null;
};

export const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
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
              path="/forgot-password"
              element={
                <PublicOnlyRoute>
                  <ForgotPasswordPage />
                </PublicOnlyRoute>
              }
            />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
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
            <Route
              path="/trips"
              element={
                <PrivateRoute>
                  <TripsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/trips/new"
              element={
                <PrivateRoute>
                  <TripCreatePage />
                </PrivateRoute>
              }
            />
            <Route
              path="/trips/:id"
              element={
                <PrivateRoute>
                  <TripDetailPage />
                </PrivateRoute>
              }
            >
              <Route path="analytics" element={<TripAnalyticsTab />} />
              <Route path="info" element={<TripInfoTab />} />
              <Route path="itinerary" element={<TripItineraryTab />} />
              <Route path="expenses" element={<TripExpensesTab />} />
              <Route path="diary" element={<TripDiaryTab />} />
            </Route>
            <Route
              path="/recommendations"
              element={
                <PrivateRoute>
                  <RecommendationsPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <PrivateRoute>
                  <ProfilePage />
                </PrivateRoute>
              }
            />

            <Route path="/auth/yandex/callback" element={<OAuthCallbackPage />} />
          </Route>
        </Routes>
        </Router>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};
