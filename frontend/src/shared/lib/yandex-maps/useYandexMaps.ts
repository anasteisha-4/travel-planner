import { useEffect, useState } from 'react'

import type { YMaps3 } from './types'

const SCRIPT_ID = 'yandex-maps-v3-script'
const SCRIPT_VERSION = '20260523-ymaps-fallback-semicolon'

let loadPromise: Promise<void> | null = null

const loadYandexMaps = (): Promise<void> => {
  if (loadPromise) return loadPromise

  loadPromise = new Promise<void>((resolve, reject) => {
    if (window.ymaps3) {
      window.ymaps3.ready.then(resolve).catch(reject)
      return
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = `/api/maps/yandex/v3?lang=ru_RU&v=${SCRIPT_VERSION}`
    script.async = true
    script.onload = () => {
      window.ymaps3.ready.then(resolve).catch(reject)
    }
    script.onerror = () => {
      loadPromise = null
      reject(new Error('Yandex Maps script failed to load'))
    }

    document.head.appendChild(script)
  })

  return loadPromise
}

export const useYandexMaps = (): { isReady: boolean; ymaps3: YMaps3 | null } => {
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    loadYandexMaps()
      .then(() => setIsReady(true))
      .catch(console.error)
  }, [])

  return {
    isReady,
    ymaps3: isReady ? window.ymaps3 : null,
  }
}
