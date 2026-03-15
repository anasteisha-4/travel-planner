import { Toaster } from '@/shared/ui';
import { Outlet } from 'react-router-dom';

export const Layout = ({ bottomNav }: { bottomNav?: React.ReactNode }) => {
  return (
    <div
      className="flex flex-col overflow-hidden bg-background text-foreground"
      style={{ height: '100dvh' }}
    >
      <main className="relative mx-auto w-full max-w-md flex-1 overflow-y-auto overscroll-contain px-4">
        <Outlet />
      </main>
      <div
        className="z-50 w-full shrink-0"
        style={{ transform: 'translateZ(0)' }}
      >
        {bottomNav}
      </div>
      <Toaster />
    </div>
  );
};
