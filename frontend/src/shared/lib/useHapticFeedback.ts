import { useCallback } from 'react';
import { useWebHaptics } from 'web-haptics/react';

type HapticVibration = {
  duration: number;
  intensity?: number;
  delay?: number;
};

export type HapticFeedback =
  | 'nudge'
  | 'success'
  | 'error'
  | 'buzz'
  | 'selection'
  | 'light'
  | 'medium'
  | 'heavy'
  | number
  | number[]
  | HapticVibration[]
  | { pattern: HapticVibration[] };

export const HAPTIC_SINGLE_TAP: HapticFeedback = {
  pattern: [{ duration: 12, intensity: 0.45 }],
};

export const HAPTIC_SINGLE_CONFIRM: HapticFeedback = {
  pattern: [{ duration: 18, intensity: 0.65 }],
};

export const HAPTIC_SINGLE_ERROR: HapticFeedback = {
  pattern: [{ duration: 26, intensity: 0.9 }],
};

export const useHapticFeedback = () => {
  const { trigger, isSupported } = useWebHaptics();

  const play = useCallback(
    (feedback: HapticFeedback = 'nudge') => {
      const resolvedFeedback =
        feedback === 'nudge'
          ? HAPTIC_SINGLE_TAP
          : feedback === 'success'
            ? HAPTIC_SINGLE_CONFIRM
            : feedback === 'error'
              ? HAPTIC_SINGLE_ERROR
              : feedback;

      void trigger(resolvedFeedback);
    },
    [trigger]
  );

  return { isSupported, play };
};
