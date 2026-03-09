import { Button } from '@/shared/ui';
import { LogOut } from 'lucide-react';

export const LogoutButton = ({ onLogout }: { onLogout: () => void }) => {
  return (
    <Button
      variant="ghost"
      onClick={onLogout}
      className="px-2 text-destructive hover:bg-destructive/10 hover:text-destructive md:px-4"
    >
      <LogOut className="h-5 w-5 md:mr-2" />
      <span className="hidden md:inline">Выйти</span>
    </Button>
  );
};
