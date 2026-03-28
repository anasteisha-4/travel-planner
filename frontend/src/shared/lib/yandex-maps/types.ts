export type LngLat = [lon: number, lat: number]

export type LngLatBounds = [LngLat, LngLat]

type YMapLocationCenter = {
  center: LngLat
  zoom: number
}

type YMapLocationBounds = {
  bounds: LngLatBounds
}

export type YMapLocationRequest = YMapLocationCenter | YMapLocationBounds

export type YMapProps = {
  location: YMapLocationRequest
  margin?: [number, number, number, number]
  theme?: 'light' | 'dark'
}

export type YMapMarkerProps = {
  coordinates: LngLat
}

export type YMapFeatureProps = {
  geometry: {
    type: 'LineString'
    coordinates: LngLat[]
  }
  style: {
    stroke?: Array<{ color: string; width: number; opacity?: number }>
  }
}

export type YMapListenerProps = {
  layer: 'any' | 'ground' | 'top'
  onClick?: (object: object | null, event: { coordinates: LngLat }) => void
}

export type YMapChild = object

export type YMapInstance = {
  destroy(): void
  addChild(child: YMapChild): void
  removeChild(child: YMapChild): void
  update(props: { location: YMapLocationRequest }): void
}

export type YMaps3 = {
  ready: Promise<void>
  YMap: new (container: HTMLElement, props: YMapProps) => YMapInstance
  YMapDefaultSchemeLayer: new () => YMapChild
  YMapDefaultFeaturesLayer: new () => YMapChild
  YMapMarker: new (props: YMapMarkerProps, element: HTMLElement) => YMapChild
  YMapFeature: new (props: YMapFeatureProps) => YMapChild
  YMapListener: new (props: YMapListenerProps) => YMapChild
}

declare global {
  interface Window {
    ymaps3: YMaps3
  }
}
