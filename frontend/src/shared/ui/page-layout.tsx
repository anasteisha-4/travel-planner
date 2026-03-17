import { cn } from '@/shared/lib/utils';

type PageLayoutProps = {
  children: React.ReactNode;
  fullScreen?: boolean;
  className?: string;
};

export const PageLayout = ({ children, fullScreen, className }: PageLayoutProps) => (
  <div
    className={cn(
      '-mx-4 flex flex-col bg-white dark:bg-stone-950',
      fullScreen ? 'h-[100dvh]' : 'h-full',
      className
    )}
  >
    {children}
  </div>
);

type AppPageHeaderProps = {
  children: React.ReactNode;
  pb?: string;
  className?: string;
};

export const AppPageHeader = ({ children, pb = 'pb-4', className }: AppPageHeaderProps) => (
  <div
    className={cn('shrink-0 px-5', pb, className)}
    style={{ paddingTop: `max(env(safe-area-inset-top, 0px), 20px)` }}
  >
    {children}
  </div>
);

type PageContentProps = {
  children: React.ReactNode;
  pb?: string;
  className?: string;
};

export const PageContent = ({ children, pb = 'pb-24', className }: PageContentProps) => (
  <div className={cn('flex-1 overflow-y-auto px-5', pb, className)}>{children}</div>
);
