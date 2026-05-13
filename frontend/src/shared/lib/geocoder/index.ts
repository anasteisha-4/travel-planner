import type { LngLat } from '../yandex-maps/types'
import { getRuntimeEnv } from '../runtime-env'
import { sendEvent } from '../../api/analytics'

const YANDEX_GEOCODER_URL = 'https://geocode-maps.yandex.ru/1.x'
const YANDEX_GEOSUGGEST_URL = 'https://suggest-maps.yandex.ru/v1/suggest'
const GEOAPIFY_URL = 'https://api.geoapify.com/v1/geocode'

export type GeocoderResult = {
  name: string
  fullAddress: string
  lat: number
  lon: number
}

type YandexGeoObject = {
  name: string
  description: string
  Point: { pos: string }
  metaDataProperty: { GeocoderMetaData: { text: string; kind: string } }
}

type YandexApiResponse = {
  response: {
    GeoObjectCollection: {
      featureMember: Array<{ GeoObject: YandexGeoObject }>
    }
  }
}

type GeosuggestItem = {
  title: { text: string }
  subtitle?: { text: string } | null
  tags?: string[]
  uri?: string
  distance?: { value: number; text: string }
  address?: { formatted_address?: string; component: Array<{ name: string; kind: string }> }
}

type GeosuggestResponse = { results?: GeosuggestItem[] }

type GeoapifyFeature = {
  geometry: { coordinates: [number, number] }
  properties: {
    name?: string
    address_line1?: string
    formatted?: string
    result_type?: string
  }
}

type GeoapifyResponse = { features: GeoapifyFeature[] }

const YANDEX_EXCLUDED_KINDS = new Set(['street', 'district'])
const GEOSUGGEST_EXCLUDED_TAGS = new Set(['street', 'district', 'province', 'country', 'other'])
const GEOAPIFY_EXCLUDED_TYPES = new Set(['street', 'suburb', 'district', 'county', 'state'])

const trackExternalGeoApi = (
  provider: 'yandex_geosuggest' | 'yandex_geocoder' | 'geoapify',
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

const isRussiaOrCIS = ([lon, lat]: LngLat): boolean =>
  lon >= 19 && lon <= 180 && lat >= 41 && lat <= 82

const parseYandex = (obj: YandexGeoObject): GeocoderResult => {
  const [lon, lat] = obj.Point.pos.split(' ').map(Number)
  return {
    name: obj.name,
    fullAddress: obj.metaDataProperty.GeocoderMetaData.text,
    lat,
    lon,
  }
}

const parseGeoapify = (feature: GeoapifyFeature): GeocoderResult => {
  const [lon, lat] = feature.geometry.coordinates
  const p = feature.properties
  return {
    name: p.name ?? p.address_line1 ?? '',
    fullAddress: p.formatted ?? '',
    lat,
    lon,
  }
}

const searchYandexGeosuggest = async (query: string, results: number, bias?: LngLat): Promise<GeocoderResult[]> => {
  const apiKey = getRuntimeEnv('VITE_YANDEX_GEOSUGGEST_API_KEY')
  const params = new URLSearchParams({
    apikey: apiKey,
    text: query,
    lang: 'ru_RU',
    results: String(results),
    types: 'biz,house,locality,metro',
    print_address: '1',
  })
  if (bias) {
    params.set('ll', `${bias[0]},${bias[1]}`)
    params.set('spn', '5,5')
  }
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${YANDEX_GEOSUGGEST_URL}?${params}`)
    trackExternalGeoApi('yandex_geosuggest', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return []
    const data: GeosuggestResponse = await resp.json()
    const items = (data.results ?? []).filter(
      (item) => !item.tags?.some((tag) => GEOSUGGEST_EXCLUDED_TAGS.has(tag)),
    )
    const resolved = await Promise.all(
      items.map(async (item) => {
        const addr = item.address?.formatted_address
        if (!addr) return null
        const geoResults = await searchYandex(addr, 1, bias)
        if (geoResults.length === 0) return null
        return { name: item.title.text, fullAddress: addr, lat: geoResults[0].lat, lon: geoResults[0].lon }
      }),
    )
    return resolved.filter((r): r is GeocoderResult => r !== null)
  } catch {
    trackExternalGeoApi('yandex_geosuggest', 0, false)
    return []
  }
}

const searchYandex = async (query: string, results: number, bias?: LngLat): Promise<GeocoderResult[]> => {
  const apiKey = getRuntimeEnv('VITE_YANDEX_MAPS_API_TOKEN')
  const params = new URLSearchParams({
    apikey: apiKey,
    format: 'json',
    lang: 'ru-RU',
    geocode: query,
    results: String(results),
  })
  if (bias) {
    params.set('ll', `${bias[0]},${bias[1]}`)
    params.set('spn', '5,5')
  }
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${YANDEX_GEOCODER_URL}?${params}`)
    trackExternalGeoApi('yandex_geocoder', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return []
    const data: YandexApiResponse = await resp.json()
    return data.response.GeoObjectCollection.featureMember
      .filter((m) => !YANDEX_EXCLUDED_KINDS.has(m.GeoObject.metaDataProperty.GeocoderMetaData.kind))
      .sort((a, b) => {
        const aIsHouse = a.GeoObject.metaDataProperty.GeocoderMetaData.kind === 'house'
        const bIsHouse = b.GeoObject.metaDataProperty.GeocoderMetaData.kind === 'house'
        if (aIsHouse === bIsHouse) return 0
        return aIsHouse ? 1 : -1
      })
      .map((m) => parseYandex(m.GeoObject))
  } catch {
    trackExternalGeoApi('yandex_geocoder', 0, false)
    return []
  }
}

const isProperName = (name: string): boolean => /[а-яёa-z]{3,}/i.test(name)

const reverseYandex = async (lat: number, lon: number): Promise<string | null> => {
  const apiKey = getRuntimeEnv('VITE_YANDEX_MAPS_API_TOKEN')
  const params = new URLSearchParams({
    apikey: apiKey,
    format: 'json',
    lang: 'ru-RU',
    geocode: `${lon},${lat}`,
    results: '1',
  })
  let geocoderName: string | null = null
  let addressText: string | null = null
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${YANDEX_GEOCODER_URL}?${params}`)
    trackExternalGeoApi('yandex_geocoder', performance.now() - startedAt, resp.ok, resp.status)
    if (resp.ok) {
      const data: YandexApiResponse = await resp.json()
      const member = data.response.GeoObjectCollection.featureMember[0]
      if (member) {
        geocoderName = member.GeoObject.name || null
        addressText = member.GeoObject.metaDataProperty.GeocoderMetaData.text
      }
    }
  } catch {
    trackExternalGeoApi('yandex_geocoder', 0, false)
    return null
  }

  if (geocoderName && isProperName(geocoderName)) return geocoderName

  const geosuggestKey = getRuntimeEnv('VITE_YANDEX_GEOSUGGEST_API_KEY')
  if (addressText && geosuggestKey) {
    try {
      const suggestParams = new URLSearchParams({
        apikey: geosuggestKey,
        text: addressText,
        lang: 'ru_RU',
        results: '1',
        types: 'biz',
        ll: `${lon},${lat}`,
        spn: '0.001,0.001',
        ull: `${lon},${lat}`,
      })
      const startedAt = performance.now()
      const suggestResp = await fetch(`${YANDEX_GEOSUGGEST_URL}?${suggestParams}`)
      trackExternalGeoApi('yandex_geosuggest', performance.now() - startedAt, suggestResp.ok, suggestResp.status)
      if (suggestResp.ok) {
        const suggestData: GeosuggestResponse = await suggestResp.json()
        const first = suggestData.results?.[0]
        if (first && (first.distance?.value ?? Infinity) < 100) return first.title.text
      }
    } catch {
      trackExternalGeoApi('yandex_geosuggest', 0, false)
    }
  }

  return geocoderName
}

const searchGeoapify = async (query: string, results: number, bias?: LngLat): Promise<GeocoderResult[]> => {
  const apiKey = getRuntimeEnv('VITE_GEOAPIFY_API_KEY')
  const params = new URLSearchParams({
    text: query,
    limit: String(results),
    lang: 'ru',
    apiKey,
  })
  if (bias) {
    params.set('bias', `proximity:${bias[0]},${bias[1]}`)
  }
  try {
    const startedAt = performance.now()
    const resp = await fetch(`${GEOAPIFY_URL}/autocomplete?${params}`)
    trackExternalGeoApi('geoapify', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return []
    const data: GeoapifyResponse = await resp.json()
    return data.features
      .filter((f) => !GEOAPIFY_EXCLUDED_TYPES.has(f.properties.result_type ?? ''))
      .filter((f) => f.properties.name ?? f.properties.address_line1)
      .map(parseGeoapify)
  } catch {
    trackExternalGeoApi('geoapify', 0, false)
    return []
  }
}

const reverseGeoapify = async (lat: number, lon: number): Promise<string | null> => {
  const apiKey = getRuntimeEnv('VITE_GEOAPIFY_API_KEY')
  const base = new URLSearchParams({ lat: String(lat), lon: String(lon), lang: 'ru', apiKey })
  try {
    const poiParams = new URLSearchParams(base)
    poiParams.set('type', 'amenity')
    const poiStartedAt = performance.now()
    const poiResp = await fetch(`${GEOAPIFY_URL}/reverse?${poiParams}`)
    trackExternalGeoApi('geoapify', performance.now() - poiStartedAt, poiResp.ok, poiResp.status)
    if (poiResp.ok) {
      const poiData: GeoapifyResponse = await poiResp.json()
      const poi = poiData.features[0]
      if (poi?.properties.name) return poi.properties.name
    }
    const startedAt = performance.now()
    const resp = await fetch(`${GEOAPIFY_URL}/reverse?${base}`)
    trackExternalGeoApi('geoapify', performance.now() - startedAt, resp.ok, resp.status)
    if (!resp.ok) return null
    const data: GeoapifyResponse = await resp.json()
    const f = data.features[0]
    return f ? (f.properties.name ?? f.properties.address_line1 ?? null) : null
  } catch {
    trackExternalGeoApi('geoapify', 0, false)
    return null
  }
}

export { useGeocode } from './useGeocode';
export { useReverseGeocode } from './useReverseGeocode';

export const searchAddress = async (query: string, results = 5, bias?: LngLat): Promise<GeocoderResult[]> => {
  const useYandex = bias ? isRussiaOrCIS(bias) : false
  if (useYandex) {
    const geosuggestKey = getRuntimeEnv('VITE_YANDEX_GEOSUGGEST_API_KEY')
    const raw = geosuggestKey
      ? await searchYandexGeosuggest(query, results, bias)
      : await searchYandex(query, results, bias)
    if (raw.length > 0) return raw.slice(0, results)
    return (await searchGeoapify(query, results, bias)).slice(0, results)
  }
  const raw = await searchGeoapify(query, results, bias)
  if (raw.length > 0) return raw.slice(0, results)
  return (await searchYandex(query, results, bias)).slice(0, results)
}

export const reverseGeocode = async (lat: number, lon: number): Promise<string | null> => {
  if (isRussiaOrCIS([lon, lat])) {
    return reverseYandex(lat, lon)
  }
  const geoapifyKey = getRuntimeEnv('VITE_GEOAPIFY_API_KEY')
  return geoapifyKey ? reverseGeoapify(lat, lon) : reverseYandex(lat, lon)
}
