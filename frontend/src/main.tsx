import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { registerSW } from 'virtual:pwa-register';
import { App } from './app/App';
import './app/styles/index.css';
import { initFrontendObservability, sendEvent } from './shared/api/analytics';

initFrontendObservability();

registerSW({
  immediate: true,
  onRegisterError(error) {
    sendEvent('service_worker_error', {
      reason_code: 'registration_failed',
      error_name: error instanceof Error ? error.name : 'unknown',
      error_message: error instanceof Error ? error.message : undefined,
    });
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
