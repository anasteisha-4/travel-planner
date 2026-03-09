import type { Trip } from '@/entities/trip';
import { CURRENCIES } from '@/shared/config';
import { cn } from '@/shared/lib/utils';
import {
  Button,
  DateInput,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
  Textarea,
} from '@/shared/ui';
import { ChevronDown, ChevronUp, Loader2, Minus, Plus } from 'lucide-react';
import { useTripForm } from '../model/useTripForm';

export const TripForm = ({
  existingTrip,
  onSuccess,
  onCancel,
}: {
  existingTrip?: Trip;
  onSuccess: (trip: Trip) => void;
  onCancel?: () => void;
}) => {
  const {
    title,
    setTitle,
    destination,
    setDestination,
    startDate,
    handleStartDateChange,
    endDate,
    setEndDate,
    budget,
    setBudget,
    currency,
    handleCurrencyChange,
    peopleCount,
    incrementPeople,
    decrementPeople,
    notes,
    setNotes,
    showNotes,
    setShowNotes,
    isLoading,
    errors,
    todayStr,
    budgetConfig,
    handleCreate,
    handleUpdate,
  } = useTripForm(existingTrip);

  const handleSubmit = async () => {
    const trip = existingTrip ? await handleUpdate(existingTrip.id) : await handleCreate();
    if (trip) onSuccess(trip);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="space-y-1.5">
        <Label className="text-sm font-medium">Название</Label>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Например: Отпуск в Турции"
          className="h-12 rounded-xl"
        />
        {errors.title && <p className="text-xs text-destructive">{errors.title}</p>}
      </div>

      <div className="grid grid-cols-[1fr,auto] items-end gap-3">
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">Направление</Label>
          <Input
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Например: Стамбул"
            className="h-12 rounded-xl"
          />
        </div>
        <div className="flex flex-col items-start space-y-1.5">
          <Label className="text-sm font-medium">Люди</Label>
          <div className="flex h-12 items-center gap-1.5 rounded-xl border bg-muted/30 px-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0 rounded-lg hover:bg-muted"
              onClick={decrementPeople}
              disabled={peopleCount <= 1}
            >
              <Minus className="h-3.5 w-3.5" />
            </Button>
            <span className="w-5 text-center text-base font-semibold tabular-nums">
              {peopleCount}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0 rounded-lg hover:bg-muted"
              onClick={incrementPeople}
              disabled={peopleCount >= 20}
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
      {(errors.destination || errors.people_count) && (
        <div className="-mt-3 flex gap-4">
          {errors.destination && (
            <p className="flex-1 text-xs text-destructive">{errors.destination}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">Начало</Label>
          <DateInput
            value={startDate}
            min={todayStr}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              handleStartDateChange(e.target.value)
            }
          />
          {errors.start_date && <p className="text-xs text-destructive">{errors.start_date}</p>}
        </div>
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">Конец</Label>
          <DateInput
            value={endDate}
            min={startDate || todayStr}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndDate(e.target.value)}
          />
          {errors.end_date && <p className="text-xs text-destructive">{errors.end_date}</p>}
        </div>
      </div>

      <div className="space-y-3">
        <Label className="text-sm font-medium">Бюджет</Label>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Select value={currency} onValueChange={handleCurrencyChange}>
              <SelectTrigger className="h-10 w-28 shrink-0 rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex-1 text-right text-lg font-semibold tabular-nums">
              {budgetConfig.format(budget[0])} — {budgetConfig.format(budget[1])}
            </div>
          </div>
          <Slider
            value={budget}
            onValueChange={(v) => setBudget(v as [number, number])}
            min={budgetConfig.min}
            max={budgetConfig.max}
            step={budgetConfig.step}
            className="py-2"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{budgetConfig.format(budgetConfig.min)}</span>
            <span>{budgetConfig.format(budgetConfig.max)}</span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex min-h-[20px] items-center justify-between">
          {showNotes && (
            <Label className="text-sm font-medium duration-200 animate-in fade-in">Заметки</Label>
          )}
          <button
            type="button"
            className="ml-auto flex items-center gap-1 text-sm text-muted-foreground"
            onClick={() => setShowNotes(!showNotes)}
          >
            {showNotes ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" /> Скрыть заметки
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" /> Добавить заметки
              </>
            )}
          </button>
        </div>

        <div
          className={cn(
            'grid transition-all duration-200 ease-in-out',
            showNotes ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
          )}
        >
          <div className="overflow-hidden">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Дополнительная информация о поездке..."
              className="mt-1.5 min-h-[100px] resize-none rounded-xl"
            />
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 flex gap-3 bg-background/80 pb-2 pt-1 backdrop-blur-sm">
        {onCancel && (
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
            className="h-12 flex-1 rounded-xl"
          >
            Отмена
          </Button>
        )}
        <Button onClick={handleSubmit} disabled={isLoading} className="h-12 flex-1 rounded-xl">
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {existingTrip ? 'Сохранить' : 'Создать'}
        </Button>
      </div>
    </div>
  );
};
