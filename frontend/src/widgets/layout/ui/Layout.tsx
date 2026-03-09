import { Toaster } from '@/shared/ui';
import { Outlet } from 'react-router-dom';

export const Layout = ({ bottomNav }: { bottomNav?: React.ReactNode }) => {
  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-background text-foreground">
      <main className="relative mx-auto w-full max-w-md flex-1 overflow-y-auto overscroll-contain px-4">
        <Outlet />
      </main>
      <div className="z-50 mx-auto w-full max-w-md shrink-0">{bottomNav}</div>
      <Toaster />
    </div>
  );
};
