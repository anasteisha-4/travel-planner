export const getCountryFlag = (countryCode?: string | null): string => {
  const normalized = countryCode?.trim().toUpperCase();
  if (!normalized || !/^[A-Z]{2}$/.test(normalized)) {
    return '🌍';
  }

  const first = normalized.codePointAt(0);
  const second = normalized.codePointAt(1);
  if (!first || !second) {
    return '🌍';
  }

  const regionalIndicatorOffset = 127_397;
  return String.fromCodePoint(first + regionalIndicatorOffset, second + regionalIndicatorOffset);
};
