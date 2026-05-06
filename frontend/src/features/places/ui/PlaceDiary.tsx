import type { PlaceVisit } from '@/entities/place';
import type { Trip } from '@/entities/trip';
import type { LngLat } from '@/shared/lib';
import { useGeocode } from '@/shared/lib';
import { cn } from '@/shared/lib/utils';
import { List, Loader2, MapIcon, Search, X } from 'lucide-react';
import { useMemo, useState } from 'react';

import { useMapSearch } from '../model/useMapSearch';
import { usePlaceDiary } from '../model/usePlaceDiary';
import { AddPlaceSheet } from './AddPlaceSheet';
import { isDiaryHintSeen } from '../model/diaryHint';
import { DiaryHintSheet } from './DiaryHintSheet';
import { PlaceDetailSheet } from './PlaceDetailSheet';
import { PlaceList } from './PlaceList';
import { PlaceMap } from './PlaceMap';

type ViewMode = 'map' | 'list';

type PlaceDiaryProps = {
  trip: Trip;
};

export const PlaceDiary = ({ trip }: PlaceDiaryProps) => {
  const {
    places,
    loading,
    selectedPlace,
    setSelectedPlace,
    handleAddPlace,
    handleUpdatePlace,
    handleDeletePlace,
    handleReorderPlaces,
  } = usePlaceDiary(trip.id);

  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [showAddSheet, setShowAddSheet] = useState(false);
  const [editingPlace, setEditingPlace] = useState<PlaceVisit | null>(null);
  const [tappedCoords, setTappedCoords] = useState<LngLat | null>(null);
  const [searchSelectedName, setSearchSelectedName] = useState<string | null>(null);
  const [flyToCoords, setFlyToCoords] = useState<LngLat | null>(null);
  const [userBiasCenter, setUserBiasCenter] = useState<LngLat | null>(null);
  const [showHint, setShowHint] = useState(() => !isDiaryHintSeen());

  const { result: destinationGeocode } = useGeocode(places.length === 0 ? trip.destination : '');

  const derivedBiasCenter = useMemo((): LngLat | null => {
    if (places.length > 0) return [parseFloat(places[0].longitude), parseFloat(places[0].latitude)];
    if (destinationGeocode) return [destinationGeocode.lon, destinationGeocode.lat];
    return null;
  }, [places, destinationGeocode]);

  const mapBiasCenter = userBiasCenter ?? derivedBiasCenter;

  const {
    searchQuery: mapSearch,
    setSearchQuery: setMapSearch,
    suggestions: mapSuggestions,
    isSearching: mapSearchLoading,
    showSuggestions: showMapSuggestions,
    clearSearch,
  } = useMapSearch(mapBiasCenter);

  const handleMapSearchSelect = (result: {
    lon: number;
    lat: number;
    name: string;
    fullAddress: string;
  }) => {
    const coords: LngLat = [result.lon, result.lat];
    setFlyToCoords(coords);
    setUserBiasCenter(coords);
    setTappedCoords(coords);
    setSearchSelectedName(result.name);
    setSelectedPlace(null);
    setEditingPlace(null);
    setShowAddSheet(true);
    clearSearch();
  };

  const handleEdit = (place: PlaceVisit) => {
    setSelectedPlace(null);
    setEditingPlace(place);
    setTappedCoords(null);
    setShowAddSheet(true);
  };

  const handleAddSuccess = (place: PlaceVisit) => {
    if (editingPlace) {
      handleUpdatePlace(place);
    } else {
      handleAddPlace(place);
    }
    setEditingPlace(null);
  };

  const handleAddClose = () => {
    setShowAddSheet(false);
    setEditingPlace(null);
    setTappedCoords(null);
    setSearchSelectedName(null);
  };

  const handleMapTapAdd = (coords: LngLat) => {
    setSelectedPlace(null);
    setEditingPlace(null);
    setTappedCoords(coords);
    setSearchSelectedName(null);
    setUserBiasCenter(coords);
    setShowAddSheet(true);
  };

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-stone-400" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 py-3">
        <div className="flex rounded-full bg-stone-100/80 p-1 dark:bg-[hsl(var(--surface-muted))]/80">
          <button
            type="button"
            onClick={() => setViewMode('map')}
            className={cn(
              'flex items-center gap-1.5 rounded-full px-4 py-1.5 text-[13px] font-semibold transition-all',
              viewMode === 'map'
                ? 'bg-white text-stone-900 shadow-sm dark:bg-stone-700 dark:text-white'
                : 'text-stone-500 dark:text-stone-400'
            )}
          >
            <MapIcon className="h-3.5 w-3.5" />
            Карта
          </button>
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className={cn(
              'flex items-center gap-1.5 rounded-full px-4 py-1.5 text-[13px] font-semibold transition-all',
              viewMode === 'list'
                ? 'bg-white text-stone-900 shadow-sm dark:bg-stone-700 dark:text-white'
                : 'text-stone-500 dark:text-stone-400'
            )}
          >
            <List className="h-3.5 w-3.5" />
            Список
          </button>
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        {viewMode === 'map' ? (
          <PlaceMap
            places={places}
            destination={trip.destination}
            selectedId={selectedPlace?.id ?? null}
            onSelectPlace={setSelectedPlace}
            onMapTap={handleMapTapAdd}
            flyToCoords={flyToCoords}
          />
        ) : (
          <PlaceList places={places} onSelectPlace={setSelectedPlace} onReorder={handleReorderPlaces} />
        )}

        {viewMode === 'map' && (
          <div className="absolute left-3 right-3 top-3 z-10">
            <div className="flex items-center gap-2 rounded-xl bg-white/95 px-3 shadow-md backdrop-blur-sm dark:bg-[hsl(var(--surface-elevated))]/95">
              {mapSearchLoading ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-stone-400" />
              ) : (
                <Search className="h-4 w-4 shrink-0 text-stone-400" />
              )}
              <input
                className="flex-1 bg-transparent py-2.5 text-[14px] text-stone-900 outline-none placeholder:text-stone-400 dark:text-white"
                placeholder="Найдите место или выберите на карте"
                value={mapSearch}
                onChange={(e) => setMapSearch(e.target.value)}
              />
              {mapSearch && (
                <button type="button" onClick={clearSearch}>
                  <X className="h-4 w-4 text-stone-400" />
                </button>
              )}
            </div>

            {showMapSuggestions && (
              <div className="mt-1 overflow-hidden rounded-xl bg-white/95 shadow-lg backdrop-blur-sm dark:bg-[hsl(var(--surface-elevated))]/95">
                {mapSuggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleMapSearchSelect(s)}
                    className="w-full px-4 py-2.5 text-left text-[13px] text-stone-800 first:pt-3 last:pb-3 hover:bg-stone-50 dark:text-stone-200 dark:hover:bg-stone-800"
                  >
                    <span className="font-semibold">{s.name}</span>
                    <span className="ml-1 text-stone-400">
                      {s.fullAddress.replace(s.name + ', ', '')}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <DiaryHintSheet open={showHint} onClose={() => setShowHint(false)} />

      <PlaceDetailSheet
        place={selectedPlace}
        onClose={() => setSelectedPlace(null)}
        onEdit={handleEdit}
        onDelete={handleDeletePlace}
      />

      <AddPlaceSheet
        open={showAddSheet}
        tripId={trip.id}
        defaultDate={trip.start_date}
        initialCoords={tappedCoords}
        initialName={searchSelectedName}
        editingPlace={editingPlace}
        onClose={handleAddClose}
        onSuccess={handleAddSuccess}
      />
    </div>
  );
};
