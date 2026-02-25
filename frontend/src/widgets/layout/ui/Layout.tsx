import { Toaster } from '@/shared/ui';
import { Outlet } from 'react-router-dom';

export const Layout = ({ bottomNav }: { bottomNav?: React.ReactNode }) => {
  return (
    <div className="min-h-[100dvh] flex flex-col bg-background text-foreground overflow-x-hidden">
      <main className="flex-1 flex flex-col w-full max-w-md mx-auto relative safe-area-top" style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom, 0px))' }}>
        <Outlet />
      </main>
      {bottomNav}
      <Toaster />
    </div>
  );
};
