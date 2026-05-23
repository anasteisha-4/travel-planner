import { sendEvent } from '../../api/analytics'
import type { LngLat } from '../yandex-maps/types'

const GEOCODE_SEARCH_URL = '/api/geocode/search'
const GEOCODE_REVERSE_URL = '/api/geocode/reverse'

export type GeocoderResult = {
  name: string
  fullAddress: string
  lat: number
  lon: number
}

const trackGeocodeApi = (
  provider: 'geocode_search' | 'geocode_reverse',
  durationMs: number,
  ok: boolean,
  status?: number,
) => {
  sendEvent('external_api_call_completed', {
    provider,
    duration_ms: Math.round(durationMs),
    ok,
    status,
  })
}

export const searchAddress = async (query: string, results = 5, bias?: LngLat): Promise<GeocoderResult[]> => {
  const params = new URLSearchParams({
    q: query,
    results: String(results),
  })
  if (bias) {
    params.set('bias_lon', String(bias[0]))
    params.set('bias_lat', String(bias[1]))
  }
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${GEOCODE_SEARCH_URL}?${params}`)
    trackGeocodeApi('geocode_search', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return []
    return ((await resp.json()) as GeocoderResult[]).slice(0, results)
  } catch {
    trackGeocodeApi('geocode_search', 0, false)
    return []
  }
}

export const reverseGeocode = async (lat: number, lon: number): Promise<string | null> => {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
  })
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${GEOCODE_REVERSE_URL}?${params}`)
    trackGeocodeApi('geocode_reverse', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return null
    const data = (await resp.json()) as { name?: string | null }
    return data.name ?? null
  } catch {
    trackGeocodeApi('geocode_reverse', 0, false)
    return null
  }
}

export { useGeocode } from './useGeocode';
export { useReverseGeocode } from './useReverseGeocode';
