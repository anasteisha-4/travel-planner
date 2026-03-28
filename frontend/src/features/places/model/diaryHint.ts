const HINT_SEEN_KEY = 'triply_diary_hint_seen';

export const isDiaryHintSeen = () => localStorage.getItem(HINT_SEEN_KEY) === '1';

export const markDiaryHintSeen = () => localStorage.setItem(HINT_SEEN_KEY, '1');
