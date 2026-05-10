import * as React from 'react';

import { HAPTIC_SINGLE_TAP, useHapticFeedback } from './useHapticFeedback';

type ScrollHapticsOptions = {
  enabled?: boolean;
  minDelta?: number;
  intervalMs?: number;
};

export const useScrollHaptics = ({
  enabled = true,
  minDelta = 22,
  intervalMs = 70,
}: ScrollHapticsOptions = {}) => {
  const { play } = useHapticFeedback();
  const activeUntil = React.useRef(0);
  const lastScrollTop = React.useRef<number | null>(null);
  const lastScrollLeft = React.useRef<number | null>(null);
  const lastTouchX = React.useRef<number | null>(null);
  const lastTouchY = React.useRef<number | null>(null);
  const accumulatedMove = React.useRef(0);
  const lastHapticAt = React.useRef(0);

  const triggerTick = React.useCallback(() => {
    const now = Date.now();
    if (now - lastHapticAt.current < intervalMs) return;
    lastHapticAt.current = now;
    play(HAPTIC_SINGLE_TAP);
  }, [intervalMs, play]);

  const markUserScroll = React.useCallback(() => {
    if (!enabled) return;
    activeUntil.current = Date.now() + 900;
  }, [enabled]);

  const handleTouchStart = React.useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      markUserScroll();
      const touch = event.touches[0];
      if (!touch) return;
      lastTouchX.current = touch.clientX;
      lastTouchY.current = touch.clientY;
      accumulatedMove.current = 0;
    },
    [markUserScroll]
  );

  const handleTouchMove = React.useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      if (!enabled) return;
      markUserScroll();

      const touch = event.touches[0];
      if (!touch) return;

      const previousX = lastTouchX.current;
      const previousY = lastTouchY.current;
      lastTouchX.current = touch.clientX;
      lastTouchY.current = touch.clientY;

      if (previousX === null || previousY === null) return;

      accumulatedMove.current += Math.max(
        Math.abs(touch.clientX - previousX),
        Math.abs(touch.clientY - previousY)
      );

      if (accumulatedMove.current < minDelta) return;

      accumulatedMove.current = 0;
      triggerTick();
    },
    [enabled, markUserScroll, minDelta, triggerTick]
  );

  const handleTouchEnd = React.useCallback(() => {
    lastTouchX.current = null;
    lastTouchY.current = null;
    accumulatedMove.current = 0;
  }, []);

  const handleWheel = React.useCallback(
    (event: React.WheelEvent<HTMLElement>) => {
      if (!enabled) return;
      markUserScroll();
      accumulatedMove.current += Math.max(Math.abs(event.deltaX), Math.abs(event.deltaY));
      if (accumulatedMove.current < minDelta) return;
      accumulatedMove.current = 0;
      triggerTick();
    },
    [enabled, markUserScroll, minDelta, triggerTick]
  );

  const handleScroll = React.useCallback(
    (event: React.UIEvent<HTMLElement>) => {
      if (!enabled || Date.now() > activeUntil.current) return;

      const target = event.currentTarget;
      const currentTop = target.scrollTop;
      const currentLeft = target.scrollLeft;
      const previousTop = lastScrollTop.current;
      const previousLeft = lastScrollLeft.current;

      lastScrollTop.current = currentTop;
      lastScrollLeft.current = currentLeft;

      if (previousTop === null || previousLeft === null) return;

      const delta = Math.max(
        Math.abs(currentTop - previousTop),
        Math.abs(currentLeft - previousLeft)
      );
      const now = Date.now();

      if (delta < minDelta || now - lastHapticAt.current < intervalMs) return;

      triggerTick();
    },
    [enabled, intervalMs, minDelta, triggerTick]
  );

  return {
    onScroll: handleScroll,
    onTouchCancel: handleTouchEnd,
    onTouchEnd: handleTouchEnd,
    onTouchMove: handleTouchMove,
    onTouchStart: handleTouchStart,
    onWheel: handleWheel,
    onPointerDown: markUserScroll,
  };
};
