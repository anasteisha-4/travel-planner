import { Outlet } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { Toaster } from './ui/toaster';

export const Layout = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground safe-area-top safe-area-left safe-area-right">

      <main className="flex-1 flex flex-col w-full max-w-md mx-auto px-4 pt-6 pb-24 relative">
        <Outlet />
      </main>

      <BottomNav />
      <Toaster />
    </div>
  );
}
