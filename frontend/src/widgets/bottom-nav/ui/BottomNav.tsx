import { cn } from '@/shared/lib/utils';
import { motion } from 'framer-motion';
import { Home, MapPin, User } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  { name: 'Главная', path: '/dashboard', icon: Home },
  { name: 'Поездки', path: '/trips', icon: MapPin },
  { name: 'Профиль', path: '/profile', icon: User },
] as const;

const HIDDEN_EXACT = new Set([
  '/login',
  '/register',
  '/onboarding',
  '/forgot-password',
  '/reset-password',
  '/trips/new',
]);

export const BottomNav = () => {
  const location = useLocation();
  const navigate = useNavigate();

  if (HIDDEN_EXACT.has(location.pathname)) return null;

  return (
    <div className="fixed bottom-0 mb-6 w-full border-t border-stone-100 bg-white pb-0 dark:border-stone-800 dark:bg-stone-950">
      <nav className="mx-auto flex max-w-md items-start justify-around px-4 pt-2">
        {NAV_ITEMS.map(({ name, path, icon: Icon }) => {
          const isActive = location.pathname === path || location.pathname.startsWith(path + '/');

          return (
            <button
              key={path}
              type="button"
              onClick={() => navigate(path)}
              className="flex flex-col items-center gap-[5px] outline-none"
            >
              {/* Icon area with shared layout indicator */}
              <div className="relative flex h-[44px] w-[44px] items-center justify-center">
                {isActive && (
                  <motion.div
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-full bg-[#2563EB]"
                    transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                  />
                )}
                <motion.div
                  className="relative z-10"
                  animate={{ scale: isActive ? 1 : 0.8 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 26 }}
                >
                  <Icon
                    className={cn(
                      'h-[22px] w-[22px] transition-colors duration-200',
                      isActive ? 'text-white' : 'text-stone-400 dark:text-stone-500'
                    )}
                    strokeWidth={isActive ? 2.3 : 1.8}
                  />
                </motion.div>
              </div>

              {/* Label */}
              <span
                className={cn(
                  'text-[10px] font-semibold leading-none tracking-wide transition-colors duration-200',
                  isActive ? 'text-[#2563EB]' : 'text-stone-400 dark:text-stone-500'
                )}
              >
                {name}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
