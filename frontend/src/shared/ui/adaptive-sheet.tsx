import { cn } from '@/shared/lib/utils';
import type { ReactNode } from 'react';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from './drawer';

type AdaptiveSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  bodyClassName?: string;
  headerClassName?: string;
  titleClassName?: string;
  showHeader?: boolean;
};

export const AdaptiveSheet = ({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  bodyClassName,
  headerClassName,
  titleClassName,
  showHeader = true,
}: AdaptiveSheetProps) => (
  <Drawer open={open} onOpenChange={onOpenChange}>
    <DrawerContent
      className={cn(
        'h-auto max-h-[calc(100dvh-env(safe-area-inset-top,0px)-8px)] w-screen overflow-hidden border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-elevated))] px-0 text-foreground shadow-[0_-18px_60px_rgba(0,0,0,0.26)]',
        'left-0 right-0 rounded-t-[28px]',
        className
      )}
    >
      <DrawerHeader className={cn(showHeader ? 'px-5 pb-4 text-left' : 'sr-only', headerClassName)}>
        <DrawerTitle
          className={cn(
            'text-[20px] font-extrabold tracking-tight text-foreground',
            titleClassName
          )}
        >
          {title}
        </DrawerTitle>
        <DrawerDescription className="text-[13px] text-muted-foreground">
          {description ?? title}
        </DrawerDescription>
      </DrawerHeader>
      <div className={cn('min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 no-scrollbar', bodyClassName)}>
        <div className="mx-auto w-full max-w-[560px]">{children}</div>
      </div>
      {footer && (
        <div
          className="shrink-0 border-t border-[hsl(var(--surface-border))] bg-[hsl(var(--surface-elevated))] px-5 py-3"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 16px)' }}
        >
          <div className="mx-auto w-full max-w-[560px]">{footer}</div>
        </div>
      )}
    </DrawerContent>
  </Drawer>
);
