import { AdaptiveSheet } from '@/shared/ui/adaptive-sheet';
import { cn } from '@/shared/lib/utils';
import { Loader2, MapPin, Star } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useFeedback } from '../model/useFeedback';

type Props = {
  open: boolean;
  onClose: () => void;
  tripId: string;
  destination: string;
};

const StarRow = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number) => void;
}) => (
  <div className="flex items-center justify-between gap-3">
    <span className="text-[14px] font-medium text-foreground">{label}</span>
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          className="p-0.5 transition-transform active:scale-90"
        >
          <Star
            className={cn(
              'h-7 w-7 transition-colors',
              value !== null && star <= value
                ? 'fill-[#F59E0B] text-[#F59E0B]'
                : 'fill-transparent text-stone-300'
            )}
          />
        </button>
      ))}
    </div>
  </div>
);

const RevisitButton = ({
  value,
  label,
  selected,
  onClick,
}: {
  value: boolean;
  label: string;
  selected: boolean;
  onClick: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={cn(
      'flex-1 rounded-[12px] border py-3 text-[14px] font-semibold transition-all active:scale-95',
      selected
        ? value
          ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
          : 'border-red-500/35 bg-red-500/10 text-red-700 dark:text-red-300'
        : 'border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] text-muted-foreground'
    )}
  >
    {label}
  </button>
);

type FormState = {
  overall: number | null;
  destRating: number | null;
  valueRating: number | null;
  wouldRevisit: boolean | null;
  freeText: string;
};

const emptyForm: FormState = {
  overall: null,
  destRating: null,
  valueRating: null,
  wouldRevisit: null,
  freeText: '',
};

export const PostTripFeedbackSheet = ({ open, onClose, tripId, destination }: Props) => {
  const { submit, isPending, existing, alreadySubmitted } = useFeedback(tripId, destination);

  const [form, setForm] = useState<FormState>(emptyForm);
  const { overall, destRating, valueRating, wouldRevisit, freeText } = form;

  const setOverall = (v: number | null) => setForm((f) => ({ ...f, overall: v }));
  const setDestRating = (v: number | null) => setForm((f) => ({ ...f, destRating: v }));
  const setValueRating = (v: number | null) => setForm((f) => ({ ...f, valueRating: v }));
  const setWouldRevisit = (v: boolean | null) => setForm((f) => ({ ...f, wouldRevisit: v }));
  const setFreeText = (v: string) => setForm((f) => ({ ...f, freeText: v }));

  const prevOpenRef = useRef(false);
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setForm(
        existing
          ? {
              overall: existing.overall_rating,
              destRating: existing.destination_rating,
              valueRating: existing.value_rating,
              wouldRevisit: existing.would_revisit,
              freeText: existing.free_text ?? '',
            }
          : emptyForm
      );
    }
    prevOpenRef.current = open;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const canSubmit = overall !== null && !isPending;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    await submit({
      trip_id: tripId,
      destination,
      overall_rating: overall,
      destination_rating: destRating,
      value_rating: valueRating,
      would_revisit: wouldRevisit,
      free_text: freeText.trim() || null,
    });
    onClose();
  };

  return (
    <AdaptiveSheet
      open={open}
      onOpenChange={(nextOpen) => !nextOpen && onClose()}
      title={alreadySubmitted ? 'Редактировать отзыв' : 'Как прошла поездка?'}
      description={destination}
      showHeader={false}
      bodyClassName="pb-6"
    >
          <div className="flex items-start justify-between pb-1 pt-0">
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-[13px] border border-primary/20 bg-primary/10">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-[16px] font-bold text-foreground">
                  {alreadySubmitted ? 'Редактировать отзыв' : 'Как прошла поездка?'}
                </p>
                <p className="text-[12px] font-medium text-muted-foreground">{destination}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-5 pt-4">
            <div className="rounded-[18px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                Общая оценка
              </p>
              <StarRow label="Поездка в целом" value={overall} onChange={setOverall} />
            </div>

            <div className="rounded-[18px] border border-[hsl(var(--surface-border))] bg-[hsl(var(--surface))] p-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                Детали
              </p>
              <div className="flex flex-col gap-3.5">
                <StarRow label="Направление" value={destRating} onChange={setDestRating} />
                <div className="h-px bg-stone-200" />
                <StarRow label="Соотношение цена / качество" value={valueRating} onChange={setValueRating} />
              </div>
            </div>

            <div>
              <p className="mb-2.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                Вернётесь снова?
              </p>
              <div className="flex gap-2.5">
                <RevisitButton
                  value={true}
                  label="Да, обязательно"
                  selected={wouldRevisit === true}
                  onClick={() => setWouldRevisit(wouldRevisit === true ? null : true)}
                />
                <RevisitButton
                  value={false}
                  label="Скорее нет"
                  selected={wouldRevisit === false}
                  onClick={() => setWouldRevisit(wouldRevisit === false ? null : false)}
                />
              </div>
            </div>

            <div>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                Впечатления (необязательно)
              </p>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                placeholder="Что запомнилось больше всего?"
                rows={3}
                className="w-full resize-none rounded-[14px] app-field px-4 py-3 text-[14px] font-medium text-foreground placeholder:italic placeholder:text-muted-foreground focus:border-primary focus:outline-none"
              />
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={cn(
                'flex h-[52px] w-full items-center justify-center rounded-[16px] text-[15px] font-bold transition-all',
                canSubmit
                  ? 'bg-primary text-primary-foreground shadow-[0_4px_16px_rgba(37,99,235,0.28)] active:scale-[0.98]'
                  : 'cursor-not-allowed bg-[hsl(var(--surface-muted))] text-muted-foreground'
              )}
            >
              {isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                alreadySubmitted ? 'Сохранить изменения' : 'Отправить отзыв'
              )}
            </button>
          </div>
    </AdaptiveSheet>
  );
};
