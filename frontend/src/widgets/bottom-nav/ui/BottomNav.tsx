import { Compass, Home, User } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

export const BottomNav = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    {
      name: '\u0413\u043b\u0430\u0432\u043d\u0430\u044f',
      path: '/dashboard',
      icon: Home,
    },
    {
      name: '\u041f\u043e\u0435\u0437\u0434\u043a\u0438',
      path: '/trips',
      icon: Compass,
    },
    {
      name: '\u041f\u0440\u043e\u0444\u0438\u043b\u044c',
      path: '/profile',
      icon: User,
    },
  ];

  const hiddenPaths = ['/login', '/register', '/onboarding', '/forgot-password', '/reset-password'];
  if (hiddenPaths.some((path) => location.pathname.startsWith(path))) {
    return null;
  }

  return (
    <div
      className="glass-panel relative w-full shrink-0 transform-gpu border-t"
      style={{
        transform: 'translateZ(0)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      <nav className="safe-area-left safe-area-right flex items-center justify-around px-2 py-3">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <button
              key={item.name}
              onClick={(e) => {
                e.preventDefault();
                navigate(item.path);
              }}
              className={`flex h-12 w-16 flex-col items-center justify-center gap-1 border-0 bg-transparent p-0 transition-all duration-200 ${
                isActive ? 'text-primary' : 'text-muted-foreground active:text-foreground/80'
              }`}
            >
              <item.icon
                className={`h-6 w-6 transition-transform ${isActive ? 'scale-110' : 'scale-100'}`}
                strokeWidth={isActive ? 2.5 : 2}
              />
              <span
                className={`text-[10px] font-medium ${isActive ? 'opacity-100' : 'opacity-80'}`}
              >
                {item.name}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
