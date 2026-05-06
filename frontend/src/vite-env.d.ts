/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_YANDEX_MAPS_API_TOKEN: string
  readonly VITE_GEOAPIFY_API_KEY: string
  readonly VITE_YANDEX_GEOSUGGEST_API_KEY: string
}

interface Navigator {
  standalone?: boolean;
}
