import { useEffect, useRef, useState } from 'react';

import { placeApi, PlaceVisitCreateSchema } from '@/entities/place';
import type { PlaceVisit } from '@/entities/place';
import { useReverseGeocode } from '@/shared/lib';
import type { LngLat } from '@/shared/lib';
import { useQueryClient } from '@tanstack/react-query';

export const useAddPlace = (
  tripId: string,
  defaultDate: string,
  editingPlace?: PlaceVisit | null,
  open?: boolean,
  initialCoords?: LngLat | null,
  initialName?: string | null,
) => {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [visitedAt, setVisitedAt] = useState(defaultDate);
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [coordsForGeocode, setCoordsForGeocode] = useState<LngLat | null>(null);
  const initialCoordsRef = useRef(initialCoords);
  const initialNameRef = useRef(initialName);

  useEffect(() => {
    initialCoordsRef.current = initialCoords;
  }, [initialCoords]);

  useEffect(() => {
    initialNameRef.current = initialName;
  }, [initialName]);

  const reversedAddress = useReverseGeocode(coordsForGeocode);

  useEffect(() => {
    if (reversedAddress && !editingPlace && open && !initialNameRef.current) setName(reversedAddress);
  }, [reversedAddress, editingPlace, open]);

  useEffect(() => {
    if (!open) return;
    if (editingPlace) {
      setName(editingPlace.name);
      setVisitedAt(editingPlace.visited_at);
      setLat(editingPlace.latitude);
      setLon(editingPlace.longitude);
      setNotes(editingPlace.notes ?? '');
      setCoordsForGeocode(null);
    } else {
      setName(initialNameRef.current ?? '');
      setVisitedAt(defaultDate);
      setLat('');
      setLon('');
      setNotes('');
      const coords = initialCoordsRef.current;
      if (coords) {
        setLat(String(coords[1]));
        setLon(String(coords[0]));
        if (!initialNameRef.current) setCoordsForGeocode(coords);
      } else {
        setCoordsForGeocode(null);
      }
    }
  }, [open, editingPlace, defaultDate]);

  const submit = async (): Promise<PlaceVisit | null> => {
    const parsed = PlaceVisitCreateSchema.safeParse({
      name,
      visited_at: visitedAt,
      latitude: lat,
      longitude: lon,
      notes: notes || null,
    });
    if (!parsed.success) return null;
    setSubmitting(true);
    try {
      const place = editingPlace
        ? await placeApi.updatePlace(editingPlace.id, parsed.data)
        : await placeApi.createPlace(tripId, parsed.data);
      queryClient.invalidateQueries({ queryKey: ['places', tripId] });
      return place;
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = PlaceVisitCreateSchema.safeParse({
    name,
    visited_at: visitedAt,
    latitude: lat,
    longitude: lon,
  }).success;

  return {
    name,
    setName,
    visitedAt,
    setVisitedAt,
    notes,
    setNotes,
    submit,
    submitting,
    isValid,
  };
};
