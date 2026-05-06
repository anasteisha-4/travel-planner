import type { PlaceVisit } from '@/entities/place';
import type { LngLat, LngLatBounds, YMapChild, YMapInstance } from '@/shared/lib';
import { useGeocode, useYandexMaps } from '@/shared/lib';
import { Loader2, Route } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const FALLBACK_CENTER: LngLat = [37.618, 55.751];

const createMarkerEl = (index: number, isSelected: boolean): HTMLDivElement => {
  const el = document.createElement('div');
  el.style.cssText = [
    'width:28px;height:28px;border-radius:50%;',
    `background:${isSelected ? '#0f172a' : '#2563EB'};`,
    'color:white;display:flex;align-items:center;justify-content:center;',
    'font-size:11px;font-weight:700;border:2px solid white;',
    'box-shadow:0 2px 8px rgba(0,0,0,0.25);cursor:pointer;',
    `transform:${isSelected ? 'scale(1.3)' : 'scale(1)'};`,
    'transition:transform 0.15s,background 0.15s;',
  ].join('');
  el.textContent = String(index + 1);
  return el;
};

const computeBounds = (places: PlaceVisit[]): LngLatBounds => {
  const lons = places.map((p) => parseFloat(p.longitude));
  const lats = places.map((p) => parseFloat(p.latitude));
  const pad = 0.02;
  return [
    [Math.min(...lons) - pad, Math.min(...lats) - pad],
    [Math.max(...lons) + pad, Math.max(...lats) + pad],
  ];
};

const computeCenter = (places: PlaceVisit[]): LngLat => {
  const lons = places.map((p) => parseFloat(p.longitude));
  const lats = places.map((p) => parseFloat(p.latitude));
  return [(Math.min(...lons) + Math.max(...lons)) / 2, (Math.min(...lats) + Math.max(...lats)) / 2];
};

type PlaceMapProps = {
  places: PlaceVisit[];
  destination: string;
  selectedId: string | null;
  onSelectPlace: (place: PlaceVisit) => void;
  onMapTap?: (coords: LngLat) => void;
  flyToCoords?: LngLat | null;
};

export const PlaceMap = ({
  places,
  destination,
  selectedId,
  onSelectPlace,
  onMapTap,
  flyToCoords,
}: PlaceMapProps) => {
  const { isReady } = useYandexMaps();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<YMapInstance | null>(null);
  const markersRef = useRef<YMapChild[]>([]);
  const routeRef = useRef<YMapChild | null>(null);
  const hasFittedRef = useRef(false);
  const onSelectRef = useRef(onSelectPlace);
  const onTapRef = useRef(onMapTap);
  const markerClickedRef = useRef(false);
  const [showRoute, setShowRoute] = useState(true);

  useEffect(() => {
    onSelectRef.current = onSelectPlace;
  }, [onSelectPlace]);

  useEffect(() => {
    onTapRef.current = onMapTap;
  }, [onMapTap]);

  // Compute center from places once on mount (stable), useQuery geocode as fallback
  const [placesCenter] = useState<LngLat | null>(() =>
    places.length > 0 ? computeCenter(places) : null
  );

  const { result: geocodeResult, isLoading: isGeocoding } = useGeocode(!placesCenter ? destination : '');
  const geocodedCenter: LngLat | null = geocodeResult
    ? [geocodeResult.lon, geocodeResult.lat]
    : !isGeocoding && !placesCenter
      ? FALLBACK_CENTER
      : null;

  const mapCenter = placesCenter ?? geocodedCenter;

  // Create map once + update markers whenever places/selectedId/showRoute change
  useEffect(() => {
    if (!isReady || !window.ymaps3 || !containerRef.current || !mapCenter) return;
    const ymaps3 = window.ymaps3;

    if (!mapRef.current) {
      const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapListener } = ymaps3;
      const map = new YMap(containerRef.current, {
        location: { center: mapCenter, zoom: places.length > 0 ? 13 : 10 },
      });
      map.addChild(new YMapDefaultSchemeLayer());
      map.addChild(new YMapDefaultFeaturesLayer());
      const tapListener = new YMapListener({
        layer: 'any',
        onClick: (_obj: object | null, event: { coordinates: LngLat }) => {
          if (markerClickedRef.current) {
            markerClickedRef.current = false;
            return;
          }
          onTapRef.current?.(event.coordinates);
        },
      });
      map.addChild(tapListener);
      mapRef.current = map;
    }

    const map = mapRef.current;

    markersRef.current.forEach((m) => map.removeChild(m));
    markersRef.current = [];
    if (routeRef.current) {
      map.removeChild(routeRef.current);
      routeRef.current = null;
    }

    places.forEach((place, i) => {
      const coords: LngLat = [parseFloat(place.longitude), parseFloat(place.latitude)];
      const el = createMarkerEl(i, place.id === selectedId);
      el.addEventListener('click', () => {
        markerClickedRef.current = true;
        onSelectRef.current(place);
      });
      const marker = new ymaps3.YMapMarker({ coordinates: coords }, el);
      map.addChild(marker);
      markersRef.current.push(marker);
    });

    if (showRoute && places.length > 1) {
      const coords = places.map((p) => [parseFloat(p.longitude), parseFloat(p.latitude)] as LngLat);
      const feature = new ymaps3.YMapFeature({
        geometry: { type: 'LineString', coordinates: coords },
        style: { stroke: [{ color: '#2563EB', width: 2, opacity: 0.45 }] },
      });
      map.addChild(feature);
      routeRef.current = feature;
    }

    if (!hasFittedRef.current && places.length > 0) {
      hasFittedRef.current = true;
      if (places.length > 1) {
        map.update({ location: { bounds: computeBounds(places) } });
      } else {
        map.update({
          location: {
            center: [parseFloat(places[0].longitude), parseFloat(places[0].latitude)],
            zoom: 14,
          },
        });
      }
    }
  }, [isReady, mapCenter, places, selectedId, showRoute]);

  useEffect(() => {
    if (!flyToCoords || !mapRef.current) return;
    mapRef.current.update({ location: { center: flyToCoords, zoom: 15 } });
  }, [flyToCoords]);

  // Destroy map only on unmount
  useEffect(() => {
    return () => {
      mapRef.current?.destroy();
      mapRef.current = null;
    };
  }, []);

  return (
    <div className="relative h-[calc(100%-92px)] w-full">
      <div ref={containerRef} className="h-full w-full" />

      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-stone-100 dark:bg-[hsl(var(--surface-elevated))]">
          <Loader2 className="h-7 w-7 animate-spin text-stone-400" />
        </div>
      )}

      {places.length > 1 && (
        <button
          type="button"
          onClick={() => setShowRoute((v) => !v)}
          className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-xl bg-white/90 shadow-md backdrop-blur-sm dark:bg-[hsl(var(--surface-muted))]/90"
          title={showRoute ? 'Скрыть маршрут' : 'Показать маршрут'}
        >
          <Route className={`h-4 w-4 ${showRoute ? 'text-[#2563EB]' : 'text-stone-400'}`} />
        </button>
      )}
    </div>
  );
};
