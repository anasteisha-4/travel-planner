type RuntimeEnvKey = `VITE_${string}`
type RuntimeEnv = Partial<Record<RuntimeEnvKey, string>>

declare global {
  interface Window {
    __TRIPLY_ENV__?: RuntimeEnv
  }
}

export const getRuntimeEnv = (key: RuntimeEnvKey): string => {
  if (typeof window !== 'undefined') {
    const runtimeValue = window.__TRIPLY_ENV__?.[key]
    if (runtimeValue) return runtimeValue
  }

  return import.meta.env[key] ?? ''
}
