'use client';

import { cn } from '@/shared/lib/utils';
import * as React from 'react';
import { Drawer as DrawerPrimitive } from 'vaul';

export const Drawer = ({ ...props }: React.ComponentProps<typeof DrawerPrimitive.Root>) => (
  <DrawerPrimitive.Root
    fixed
    handleOnly
    repositionInputs={false}
    scrollLockTimeout={0}
    {...props}
  />
);

export const DrawerTrigger = ({
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Trigger>) => <DrawerPrimitive.Trigger {...props} />;

export const DrawerPortal = ({ ...props }: React.ComponentProps<typeof DrawerPrimitive.Portal>) => (
  <DrawerPrimitive.Portal {...props} />
);

export const DrawerClose = ({ ...props }: React.ComponentProps<typeof DrawerPrimitive.Close>) => (
  <DrawerPrimitive.Close {...props} />
);

export const DrawerHandle = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof DrawerPrimitive.Handle>) => (
  <DrawerPrimitive.Handle
    className={cn(
      'mx-100 mb-5 mt-3 h-1 w-full shrink-0 touch-none !bg-transparent',
      '[&_[data-vaul-handle-hitarea]]:flex [&_[data-vaul-handle-hitarea]]:items-center [&_[data-vaul-handle-hitarea]]:justify-center',
      className
    )}
    {...props}
  >
    {children ?? (
      <span className="pointer-events-none h-1 w-10 rounded-full bg-slate-300/80 dark:bg-slate-600/80" />
    )}
  </DrawerPrimitive.Handle>
);

export const DrawerOverlay = React.forwardRef<
  React.ElementRef<typeof DrawerPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DrawerPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DrawerPrimitive.Overlay
    ref={ref}
    className={cn('fixed inset-0 z-50 bg-black/50', className)}
    {...props}
  />
));
DrawerOverlay.displayName = 'DrawerOverlay';

export const DrawerContent = React.forwardRef<
  React.ElementRef<typeof DrawerPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DrawerPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DrawerPortal>
    <DrawerOverlay />
    <DrawerPrimitive.Content
      ref={ref}
      className={cn(
        'fixed inset-x-0 bottom-0 z-50 flex w-screen flex-col bg-background px-5',
        'max-h-[calc(100dvh-env(safe-area-inset-top,0px)-8px)] rounded-t-3xl border-t',
        className
      )}
      {...props}
    >
      <DrawerHandle />
      {children}
    </DrawerPrimitive.Content>
  </DrawerPortal>
));
DrawerContent.displayName = 'DrawerContent';

export const DrawerHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col gap-0.5 text-center', className)} {...props} />
);

export const DrawerFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mt-auto flex flex-col gap-2 p-4', className)} {...props} />
);

export const DrawerTitle = React.forwardRef<
  React.ElementRef<typeof DrawerPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DrawerPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DrawerPrimitive.Title
    ref={ref}
    className={cn('font-semibold text-foreground', className)}
    {...props}
  />
));
DrawerTitle.displayName = 'DrawerTitle';

export const DrawerDescription = React.forwardRef<
  React.ElementRef<typeof DrawerPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DrawerPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DrawerPrimitive.Description
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));
DrawerDescription.displayName = 'DrawerDescription';
