import { Compass, Home, User } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

export const BottomNav = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    {
      name: '\u0413\u043b\u0430\u0432\u043d\u0430\u044f',
      path: '/dashboard',
      icon: Home
    },
    {
      name: '\u041f\u043e\u0435\u0437\u0434\u043a\u0438',
      path: '/trips',
      icon: Compass
    },
    {
      name: '\u041f\u0440\u043e\u0444\u0438\u043b\u044c',
      path: '/profile',
      icon: User
    }
  ];


  const hiddenPaths = ['/login', '/register', '/onboarding', '/forgot-password', '/reset-password'];
  if (hiddenPaths.some(path => location.pathname.startsWith(path))) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 glass-panel border-t" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
      <nav className="flex items-center justify-around px-2 py-3 safe-area-left safe-area-right">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <button
              key={item.name}
              onClick={(e) => {
                e.preventDefault();
                navigate(item.path);
              }}
              className={`flex flex-col items-center justify-center w-16 h-12 gap-1 transition-all duration-200 bg-transparent border-0 p-0 ${
                isActive 
                  ? 'text-primary' 
                  : 'text-muted-foreground active:text-foreground/80'
              }`}
            >
              <item.icon 
                className={`w-6 h-6 transition-transform ${
                  isActive ? 'scale-110' : 'scale-100'
                }`} 
                strokeWidth={isActive ? 2.5 : 2}
              />
              <span className={`text-[10px] font-medium ${isActive ? 'opacity-100' : 'opacity-80'}`}>
                {item.name}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
