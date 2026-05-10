import * as SliderPrimitive from '@radix-ui/react-slider';
import * as React from 'react';

import {
  HAPTIC_SINGLE_CONFIRM,
  HAPTIC_SINGLE_TAP,
  useHapticFeedback,
  type HapticFeedback,
} from '@/shared/lib/useHapticFeedback';
import { cn } from '@/shared/lib/utils';

type SliderProps = React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root> & {
  haptic?: boolean | HapticFeedback;
};

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(
  (
    {
      className,
      haptic = true,
      onPointerDown,
      onValueChange,
      onValueCommit,
      ...props
    },
    ref
  ) => {
    const { play } = useHapticFeedback();
    const lastHapticAt = React.useRef(0);
    const lastValueKey = React.useRef('');

    const playSliderHaptic = (fallback: HapticFeedback, value?: number[]) => {
      if (!haptic) return;
      const nextKey = value?.join(':') ?? '';
      const now = Date.now();
      if ((nextKey && nextKey === lastValueKey.current) || now - lastHapticAt.current < 80) return;
      lastValueKey.current = nextKey;
      lastHapticAt.current = now;
      play(
        haptic === true
          ? fallback === 'success'
            ? HAPTIC_SINGLE_CONFIRM
            : HAPTIC_SINGLE_TAP
          : haptic
      );
    };

    return (
      <SliderPrimitive.Root
        ref={ref}
        className={cn('relative flex w-full touch-none select-none items-center', className)}
        onPointerDown={(event) => {
          playSliderHaptic('nudge');
          onPointerDown?.(event);
        }}
        onValueChange={(value) => {
          playSliderHaptic('nudge', value);
          onValueChange?.(value);
        }}
        onValueCommit={(value) => {
          playSliderHaptic('success', value);
          onValueCommit?.(value);
        }}
        {...props}
      >
        <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-primary/20">
          <SliderPrimitive.Range className="absolute h-full bg-primary" />
        </SliderPrimitive.Track>
        {(props.value || props.defaultValue || [0]).map((_, i) => (
          <SliderPrimitive.Thumb
            key={i}
            className="block h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          />
        ))}
      </SliderPrimitive.Root>
    );
  }
);
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
