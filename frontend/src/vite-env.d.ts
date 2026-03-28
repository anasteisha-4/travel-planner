/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_YANDEX_MAPS_API_TOKEN: string
}

interface Navigator {
  standalone?: boolean;
}
