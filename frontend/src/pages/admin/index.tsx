import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/ui';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  BarChart3,
  Database,
  ExternalLink,
  Gauge,
  LayoutDashboard,
  LockKeyhole,
  MapPin,
  RefreshCw,
  Search,
  Settings2,
  Shield,
  Signal,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import { getRuntimeEnv } from '@/shared/lib/runtime-env';
import {
  createMLDatasetSnapshot,
  approveLLMCandidateDestination,
  approveLLMCandidatePOI,
  getAdminEvents,
  getBudgetDebug,
  getDashboardSummary,
  getExperimentReport,
  getExperiments,
  getFeatureFlags,
  getItineraryDebug,
  getLLMCandidateDestinations,
  getLLMCandidatePOI,
  getLLMReviewLogs,
  getMLDatasetReport,
  getModelRegistry,
  getRecommendationDebug,
  getTimeline,
  markLLMCandidateDestinationNeedsData,
  markLLMCandidatePOINeedsData,
  rejectLLMCandidateDestination,
  rejectLLMCandidatePOI,
  updateFeatureFlag,
  type AdminEvent,
  type EventsFilters,
  type LLMCandidatePOIApprovePayload,
  type LLMCandidateDestination,
  type LLMCandidatePOI,
  type LLMReviewLog,
} from './api';

const DEFAULT_GRAFANA_DASHBOARD_URL =
  '/grafana/d/triply-analytics/triply-analytics?orgId=1&from=now-14d&to=now';

const getDefaultGrafanaDashboardUrl = () => {
  if (typeof window === 'undefined') return DEFAULT_GRAFANA_DASHBOARD_URL;
  const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  if (!isLocalhost) return DEFAULT_GRAFANA_DASHBOARD_URL;
  return `http://${window.location.hostname}:3001${DEFAULT_GRAFANA_DASHBOARD_URL}`;
};

const formatEventName = (value: string) => value.split('_').join(' ');
const formatDate = (value?: string | null) => value?.slice(0, 19).replace('T', ' ') ?? '-';

const JsonBlock = ({ value, maxHeight = 'max-h-56' }: { value: unknown; maxHeight?: string }) => (
  <pre className={`${maxHeight} overflow-auto rounded-md bg-muted/60 p-3 text-xs`}>
    {JSON.stringify(value ?? {}, null, 2)}
  </pre>
);

const fieldList = (value: unknown): string[] => (Array.isArray(value) ? value.map(String) : []);

const ReviewLogRow = ({ log }: { log: LLMReviewLog }) => (
  <div className="grid gap-3 rounded-lg border p-3 text-sm xl:grid-cols-[120px_130px_1fr_110px_160px] xl:items-center">
    <div>
      <Badge variant={log.status === 'ok' ? 'default' : 'outline'}>{log.status}</Badge>
      <div className="mt-1 text-xs text-muted-foreground">{formatDate(log.created_at)}</div>
    </div>
    <div>
      <div className="font-medium">{log.entity_type}</div>
      <div className="truncate text-xs text-muted-foreground">{log.entity_id ?? '-'}</div>
    </div>
    <div className="min-w-0">
      <div className="truncate font-medium">
        {log.provider} / {log.model}
      </div>
      <div className="truncate text-xs text-muted-foreground">{log.prompt_version}</div>
    </div>
    <div className="tabular-nums text-muted-foreground">
      {log.latency_ms !== null ? `${log.latency_ms} мс` : '-'}
    </div>
    <div className="flex flex-wrap gap-1">
      {log.issue_codes.length > 0 ? (
        log.issue_codes.slice(0, 4).map((code) => (
          <Badge key={code} variant="outline" className="max-w-full truncate">
            {code}
          </Badge>
        ))
      ) : (
        <span className="text-xs text-muted-foreground">Без issue codes</span>
      )}
    </div>
  </div>
);

const CandidatePOICard = ({
  candidate,
  onApprove,
  onReject,
  onNeedsData,
  isBusy,
}: {
  candidate: LLMCandidatePOI;
  onApprove: (id: string, payload: LLMCandidatePOIApprovePayload) => void;
  onReject: (id: string) => void;
  onNeedsData: (id: string) => void;
  isBusy: boolean;
}) => {
  const sourceUrl = String(candidate.payload.source_url ?? candidate.payload.official_url ?? '');
  const validation =
    typeof candidate.payload.validation === 'object' && candidate.payload.validation !== null
      ? (candidate.payload.validation as Record<string, unknown>)
      : {};
  const missingFields = fieldList(candidate.payload.missing_fields).concat(
    fieldList(validation.missing_fields)
  );
  const duplicateWarnings = fieldList(validation.duplicate_warnings);
  const priceEstimate = candidate.payload.estimated_price;
  const priceCurrency = candidate.payload.estimated_price_currency;
  const priceSource = String(candidate.payload.price_source_url ?? '');
  const [draft, setDraft] = useState({
    name: candidate.name,
    name_ru: String(candidate.payload.name_ru ?? ''),
    category: candidate.category ?? '',
    lat: candidate.lat?.toString() ?? '',
    lng: candidate.lng?.toString() ?? '',
    address: candidate.address ?? '',
    source_url: String(candidate.payload.source_url ?? ''),
    official_url: String(candidate.payload.official_url ?? ''),
    suggested_visit_duration_minutes: String(candidate.payload.suggested_visit_duration_minutes ?? ''),
    opening_hours: String(candidate.payload.opening_hours ?? ''),
    estimated_price: typeof priceEstimate === 'number' ? String(priceEstimate) : '',
    estimated_price_currency: String(priceCurrency ?? ''),
    price_source_url: priceSource,
  });
  const updateDraft = (key: keyof typeof draft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const approvePayload = (): LLMCandidatePOIApprovePayload => {
    const numeric = (value: string) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : undefined;
    };
    return {
      name: draft.name.trim(),
      name_ru: draft.name_ru.trim() || undefined,
      category: draft.category.trim(),
      lat: numeric(draft.lat),
      lng: numeric(draft.lng),
      address: draft.address.trim() || undefined,
      source_url: draft.source_url.trim() || undefined,
      official_url: draft.official_url.trim() || undefined,
      suggested_visit_duration_minutes: numeric(draft.suggested_visit_duration_minutes),
      opening_hours: draft.opening_hours.trim() || undefined,
      estimated_price: numeric(draft.estimated_price),
      estimated_price_currency: draft.estimated_price_currency.trim() || undefined,
      price_source_url: draft.price_source_url.trim() || undefined,
    };
  };

  return (
    <Card className="rounded-lg">
      <CardContent className="grid gap-4 p-4 xl:grid-cols-[1fr_280px]">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold">{candidate.name}</h3>
            <Badge variant={candidate.status === 'pending' ? 'default' : 'outline'}>
              {candidate.status}
            </Badge>
            {candidate.category && <Badge variant="outline">{candidate.category}</Badge>}
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
            <div>Destination: {candidate.destination_id ?? '-'}</div>
            <div>
              Coordinates:{' '}
              {candidate.lat !== null && candidate.lng !== null
                ? `${candidate.lat.toFixed(5)}, ${candidate.lng.toFixed(5)}`
                : '-'}
            </div>
            <div>Trip: {candidate.trip_id ?? '-'}</div>
            <div>Itinerary: {candidate.itinerary_id ?? '-'}</div>
            <div>Confidence: {String(candidate.payload.confidence ?? '-')}</div>
            <div>Missing: {missingFields.length ? missingFields.join(', ') : '-'}</div>
            <div>
              Price:{' '}
              {typeof priceEstimate === 'number'
                ? `${priceEstimate} ${String(priceCurrency ?? '')}`.trim()
                : '-'}
            </div>
            <div>Price checked: {String(candidate.payload.price_checked_at ?? '-')}</div>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <Input value={draft.name} onChange={(event) => updateDraft('name', event.target.value)} placeholder="Название" disabled={isBusy} />
            <Input value={draft.name_ru} onChange={(event) => updateDraft('name_ru', event.target.value)} placeholder="Русское название" disabled={isBusy} />
            <Input value={draft.category} onChange={(event) => updateDraft('category', event.target.value)} placeholder="Категория" disabled={isBusy} />
            <Input value={draft.suggested_visit_duration_minutes} onChange={(event) => updateDraft('suggested_visit_duration_minutes', event.target.value)} placeholder="Минуты посещения" disabled={isBusy} />
            <Input value={draft.lat} onChange={(event) => updateDraft('lat', event.target.value)} placeholder="Lat" disabled={isBusy} />
            <Input value={draft.lng} onChange={(event) => updateDraft('lng', event.target.value)} placeholder="Lng" disabled={isBusy} />
            <Input className="md:col-span-2" value={draft.address} onChange={(event) => updateDraft('address', event.target.value)} placeholder="Адрес" disabled={isBusy} />
            <Input value={draft.source_url} onChange={(event) => updateDraft('source_url', event.target.value)} placeholder="Source URL" disabled={isBusy} />
            <Input value={draft.official_url} onChange={(event) => updateDraft('official_url', event.target.value)} placeholder="Official URL" disabled={isBusy} />
            <Input value={draft.opening_hours} onChange={(event) => updateDraft('opening_hours', event.target.value)} placeholder="Часы работы" disabled={isBusy} />
            <Input value={draft.estimated_price} onChange={(event) => updateDraft('estimated_price', event.target.value)} placeholder="Цена" disabled={isBusy} />
            <Input value={draft.estimated_price_currency} onChange={(event) => updateDraft('estimated_price_currency', event.target.value)} placeholder="Валюта цены" disabled={isBusy} />
            <Input value={draft.price_source_url} onChange={(event) => updateDraft('price_source_url', event.target.value)} placeholder="Источник цены" disabled={isBusy} />
          </div>
          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary"
            >
              Источник
              <ExternalLink className="size-3.5" />
            </a>
          )}
          <JsonBlock
            value={{
              reason: candidate.payload.reason,
              validation,
              duplicate_warnings: duplicateWarnings,
              price_evidence: {
                estimated_price: priceEstimate,
                currency: priceCurrency,
                source_url: priceSource || null,
                checked_at: candidate.payload.price_checked_at,
              },
              review_comment: candidate.review_comment,
              approved_poi_id: candidate.approved_poi_id,
            }}
            maxHeight="max-h-40"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Button
            onClick={() => onApprove(candidate.id, approvePayload())}
            disabled={isBusy || candidate.status === 'approved'}
          >
            Одобрить
          </Button>
          <Button
            variant="outline"
            onClick={() => onNeedsData(candidate.id)}
            disabled={isBusy || candidate.status === 'approved'}
          >
            Нужны данные
          </Button>
          <Button
            variant="outline"
            className="text-destructive"
            onClick={() => onReject(candidate.id)}
            disabled={isBusy || candidate.status === 'approved'}
          >
            Отклонить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const CandidateDestinationCard = ({
  candidate,
  onApprove,
  onReject,
  onNeedsData,
  isBusy,
}: {
  candidate: LLMCandidateDestination;
  onApprove: (id: string, payload: { name_ru?: string; region?: string }) => void;
  onReject: (id: string) => void;
  onNeedsData: (id: string) => void;
  isBusy: boolean;
}) => {
  const sourceUrls = fieldList(candidate.payload.source_urls);
  const initialNameRu = typeof candidate.payload.name_ru === 'string' ? candidate.payload.name_ru : '';
  const [nameRu, setNameRu] = useState(initialNameRu);
  const [region, setRegion] = useState(candidate.region ?? String(candidate.payload.region ?? ''));
  const mapUrl =
    candidate.lat !== null && candidate.lng !== null
      ? `https://yandex.ru/maps/?ll=${candidate.lng},${candidate.lat}&z=12&pt=${candidate.lng},${candidate.lat}`
      : null;

  return (
    <Card className="rounded-lg">
      <CardContent className="grid gap-4 p-4 xl:grid-cols-[1fr_280px]">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold">{candidate.name}</h3>
            <Badge variant={candidate.status === 'pending' ? 'default' : 'outline'}>
              {candidate.status}
            </Badge>
            {candidate.country_code && <Badge variant="outline">{candidate.country_code}</Badge>}
          </div>
          <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
            <div>Страна: {candidate.country_name ?? '-'}</div>
            <div>Регион: {candidate.region ?? '-'}</div>
            <div>
              Координаты:{' '}
              {candidate.lat !== null && candidate.lng !== null
                ? `${candidate.lat.toFixed(5)}, ${candidate.lng.toFixed(5)}`
                : '-'}
            </div>
            <div>Поездка: {candidate.trip_id ?? '-'}</div>
            <div>Confidence: {String(candidate.payload.confidence ?? '-')}</div>
            <div>Review: {candidate.review_comment ?? '-'}</div>
          </div>
          <div className="grid gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground" htmlFor={`candidate-destination-name-ru-${candidate.id}`}>
              Русское название
            </label>
            <Input
              id={`candidate-destination-name-ru-${candidate.id}`}
              value={nameRu}
              onChange={(event) => setNameRu(event.target.value)}
              placeholder="Например: Салоу"
              disabled={isBusy}
            />
          </div>
          <div className="grid gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground" htmlFor={`candidate-destination-region-${candidate.id}`}>
              Регион
            </label>
            <Input
              id={`candidate-destination-region-${candidate.id}`}
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              placeholder="Например: Europe"
              disabled={isBusy}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {mapUrl && (
              <a
                href={mapUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                Карта
                <ExternalLink className="size-3.5" />
              </a>
            )}
            {sourceUrls.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                Источник
                <ExternalLink className="size-3.5" />
              </a>
            ))}
          </div>
          <JsonBlock
            value={{
              reason: candidate.payload.reason,
              source_urls: candidate.payload.source_urls,
              route_note: 'Одобрение добавляет направление в каталог и связывает POI-кандидаты этой поездки.',
            }}
            maxHeight="max-h-44"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Button
            onClick={() =>
              onApprove(candidate.id, {
                name_ru: nameRu.trim() || undefined,
                region: region.trim() || undefined,
              })
            }
            disabled={isBusy}
          >
            {candidate.status === 'approved' ? 'Синхронизировать каталог' : 'Одобрить в каталог'}
          </Button>
          <Button
            variant="outline"
            onClick={() => onNeedsData(candidate.id)}
            disabled={isBusy || candidate.status === 'approved'}
          >
            Нужны данные
          </Button>
          <Button
            variant="destructive"
            onClick={() => onReject(candidate.id)}
            disabled={isBusy || candidate.status === 'approved'}
          >
            Отклонить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const MetricGrid = ({ title, counts }: { title: string; counts: Record<string, number> }) => (
  <section className="space-y-3">
    <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">
      {title}
    </h2>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {Object.entries(counts).map(([key, value]) => (
        <Card key={key} className="rounded-lg shadow-sm">
          <CardContent className="p-4">
            <div className="text-2xl font-semibold tabular-nums">{value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{formatEventName(key)}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  </section>
);

const numericValue = (value: unknown) =>
  typeof value === 'number' && Number.isFinite(value) ? value : 0;

const LineChart = ({
  title,
  data,
  series,
}: {
  title: string;
  data: Array<Record<string, number | string | null>>;
  series: Array<{ key: string; label: string; color: string }>;
}) => {
  const width = 760;
  const height = 230;
  const padding = 30;
  const maxValue = Math.max(
    1,
    ...data.flatMap((row) => series.map((item) => numericValue(row[item.key])))
  );
  const xStep = data.length > 1 ? (width - padding * 2) / (data.length - 1) : 0;
  const y = (value: number) => height - padding - (value / maxValue) * (height - padding * 2);
  const x = (index: number) => padding + index * xStep;

  return (
    <Card className="rounded-lg">
      <CardHeader className="p-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <BarChart3 className="size-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <svg viewBox={`0 0 ${width} ${height}`} className="h-[260px] w-full overflow-visible">
          {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
            <g key={tick}>
              <line
                x1={padding}
                x2={width - padding}
                y1={padding + (height - padding * 2) * tick}
                y2={padding + (height - padding * 2) * tick}
                className="stroke-border"
              />
            </g>
          ))}
          {series.map((item) => {
            const points = data
              .map((row, index) => `${x(index)},${y(numericValue(row[item.key]))}`)
              .join(' ');
            return (
              <polyline
                key={item.key}
                points={points}
                fill="none"
                stroke={item.color}
                strokeWidth="3"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}
          {data.map((row, index) => (
            <text
              key={String(row.date)}
              x={x(index)}
              y={height - 5}
              textAnchor="middle"
              className="fill-muted-foreground text-[10px]"
            >
              {String(row.date ?? '').slice(5)}
            </text>
          ))}
        </svg>
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          {series.map((item) => (
            <span key={item.key} className="inline-flex items-center gap-2">
              <span className="size-2 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const BarList = ({
  title,
  items,
}: {
  title: string;
  items: Array<{ label: string; value: number }>;
}) => {
  const maxValue = Math.max(1, ...items.map((item) => item.value));
  return (
    <Card className="rounded-lg">
      <CardHeader className="p-4">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-4 pt-0">
        {items.map((item) => (
          <div
            key={item.label}
            className="grid grid-cols-[190px_1fr_64px] items-center gap-3 text-sm"
          >
            <span className="truncate text-muted-foreground">{formatEventName(item.label)}</span>
            <div className="h-2 rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-primary"
                style={{ width: `${Math.max(4, (item.value / maxValue) * 100)}%` }}
              />
            </div>
            <span className="text-right font-medium tabular-nums">{item.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

const FunnelChart = ({
  title,
  rows,
}: {
  title: string;
  rows: Array<{ event_type: string; count: number; conversion: number | null }>;
}) => {
  const maxValue = Math.max(1, ...rows.map((row) => row.count));
  return (
    <Card className="rounded-lg">
      <CardHeader className="p-4">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-4 pt-0">
        {rows.map((row) => (
          <div key={row.event_type} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">{formatEventName(row.event_type)}</span>
              <span className="font-medium tabular-nums">
                {row.count}{' '}
                {row.conversion === null ? '' : `· ${Math.round(row.conversion * 100)}%`}
              </span>
            </div>
            <div className="h-7 rounded-sm bg-muted">
              <div
                className="h-7 rounded-sm bg-foreground/80"
                style={{ width: `${Math.max(3, (row.count / maxValue) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

const EventRow = ({ event }: { event: AdminEvent }) => (
  <div className="grid gap-2 border-b py-3 text-sm md:grid-cols-[180px_1fr_190px]">
    <div>
      <div className="font-medium">{event.event_type}</div>
      <div className="text-xs text-muted-foreground">{formatDate(event.created_at)}</div>
    </div>
    <JsonBlock value={event.context} maxHeight="max-h-28" />
    <div className="min-w-0 text-xs text-muted-foreground">
      <div className="truncate">user: {event.user_id ?? 'anonymous'}</div>
      <div className="truncate">entity: {event.entity_id ?? '-'}</div>
      <div className="truncate">session: {event.session_id}</div>
    </div>
  </div>
);

const DiagnosticsCard = ({
  title,
  value,
  onChange,
  onSearch,
  children,
}: {
  title: string;
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  children: ReactNode;
}) => (
  <Card className="rounded-lg">
    <CardHeader className="gap-3 p-4 md:flex-row md:items-center md:justify-between">
      <CardTitle className="text-base">{title}</CardTitle>
      <div className="flex w-full gap-2 md:w-auto">
        <Input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="id"
          className="h-10 md:w-72"
        />
        <Button variant="outline" onClick={onSearch} disabled={!value}>
          <Search className="size-4" />
        </Button>
      </div>
    </CardHeader>
    <CardContent className="p-4 pt-0">{children}</CardContent>
  </Card>
);

export const AdminPage = () => {
  const queryClient = useQueryClient();
  const [eventFilters, setEventFilters] = useState<EventsFilters>({});
  const [selectedExperiment, setSelectedExperiment] = useState('');
  const [recommendationId, setRecommendationId] = useState('');
  const [activeRecommendationId, setActiveRecommendationId] = useState('');
  const [budgetTripId, setBudgetTripId] = useState('');
  const [activeBudgetTripId, setActiveBudgetTripId] = useState('');
  const [itineraryTripId, setItineraryTripId] = useState('');
  const [activeItineraryTripId, setActiveItineraryTripId] = useState('');

  const summaryQuery = useQuery({
    queryKey: ['admin-dashboard-summary'],
    queryFn: getDashboardSummary,
  });
  const eventsQuery = useQuery({
    queryKey: ['admin-events', eventFilters],
    queryFn: () => getAdminEvents(eventFilters),
  });
  const timelineQuery = useQuery({
    queryKey: ['admin-timeline', eventFilters.userId, eventFilters.sessionId],
    queryFn: () => getTimeline(eventFilters),
  });
  const flagsQuery = useQuery({ queryKey: ['admin-feature-flags'], queryFn: getFeatureFlags });
  const experimentsQuery = useQuery({ queryKey: ['admin-experiments'], queryFn: getExperiments });
  const experimentReportQuery = useQuery({
    queryKey: ['admin-experiment-report', selectedExperiment],
    queryFn: () => getExperimentReport(selectedExperiment),
    enabled: Boolean(selectedExperiment),
  });
  const mlDatasetQuery = useQuery({
    queryKey: ['admin-ml-dataset-report'],
    queryFn: getMLDatasetReport,
  });
  const modelsQuery = useQuery({ queryKey: ['admin-model-registry'], queryFn: getModelRegistry });
  const llmCandidatesQuery = useQuery({
    queryKey: ['admin-llm-candidate-poi'],
    queryFn: getLLMCandidatePOI,
  });
  const llmReviewLogsQuery = useQuery({
    queryKey: ['admin-llm-review-logs'],
    queryFn: getLLMReviewLogs,
  });
  const llmDestinationCandidatesQuery = useQuery({
    queryKey: ['admin-llm-candidate-destination'],
    queryFn: getLLMCandidateDestinations,
  });
  const recommendationDebugQuery = useQuery({
    queryKey: ['admin-recommendation-debug', activeRecommendationId],
    queryFn: () => getRecommendationDebug(activeRecommendationId),
    enabled: Boolean(activeRecommendationId),
  });
  const budgetDebugQuery = useQuery({
    queryKey: ['admin-budget-debug', activeBudgetTripId],
    queryFn: () => getBudgetDebug(activeBudgetTripId),
    enabled: Boolean(activeBudgetTripId),
  });
  const itineraryDebugQuery = useQuery({
    queryKey: ['admin-itinerary-debug', activeItineraryTripId],
    queryFn: () => getItineraryDebug(activeItineraryTripId),
    enabled: Boolean(activeItineraryTripId),
  });

  const flagMutation = useMutation({
    mutationFn: updateFeatureFlag,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-feature-flags'] }),
  });
  const snapshotMutation = useMutation({
    mutationFn: createMLDatasetSnapshot,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-ml-dataset-report'] }),
  });
  const candidateActionMutation = useMutation({
    mutationFn: ({
      id,
      action,
      payload,
    }: {
      id: string;
      action: 'approve' | 'reject' | 'needs_data';
      payload?: LLMCandidatePOIApprovePayload;
    }) => {
      if (action === 'approve') return approveLLMCandidatePOI(id, payload);
      if (action === 'reject') return rejectLLMCandidatePOI(id);
      return markLLMCandidatePOINeedsData(id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-llm-candidate-poi'] }),
  });
  const candidateDestinationActionMutation = useMutation({
    mutationFn: ({
      id,
      action,
      payload,
    }: {
      id: string;
      action: 'approve' | 'reject' | 'needs_data';
      payload?: { name_ru?: string; region?: string };
    }) => {
      if (action === 'approve') return approveLLMCandidateDestination(id, payload);
      if (action === 'reject') return rejectLLMCandidateDestination(id);
      return markLLMCandidateDestinationNeedsData(id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-llm-candidate-destination'] }),
  });

  const summary = summaryQuery.data;
  const recentEvents = useMemo(
    () => eventsQuery.data?.events ?? summary?.recent_events ?? [],
    [eventsQuery.data, summary]
  );
  const grafanaDashboardUrl =
    getRuntimeEnv('VITE_GRAFANA_DASHBOARD_URL') || getDefaultGrafanaDashboardUrl();
  const openGrafanaDashboard = () => {
    const navigate = () => {
      window.location.assign(grafanaDashboardUrl);
    };

    if (!('serviceWorker' in navigator)) {
      navigate();
      return;
    }

    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
      .finally(navigate);
  };

  if (summaryQuery.error) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Card className="rounded-lg border-destructive/40">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 text-destructive">
              <Shield className="size-5" />
              <div className="font-medium">Нет доступа к админ-панели</div>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Проверьте, что ваш user id есть в списке администраторов
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="h-dvh min-w-[1280px] overflow-auto bg-muted/20 px-6 py-6">
      <header className="mx-auto flex max-w-[1680px] flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Signal className="size-4" />
            Triply intelligence
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">
            Triply Admin Command Center
          </h1>
        </div>
        <Button
          variant="outline"
          onClick={() => summaryQuery.refetch()}
          disabled={summaryQuery.isFetching}
        >
          <RefreshCw className="size-4" />
          Обновить
        </Button>
      </header>

      <Tabs
        defaultValue="dashboards"
        className="mx-auto mt-6 grid max-w-[1680px] gap-6 xl:grid-cols-[240px_1fr]"
      >
        <aside className="rounded-lg border bg-background p-3 shadow-sm">
          <TabsList className="grid h-auto w-full gap-1 bg-transparent p-0">
            <TabsTrigger value="dashboards" className="justify-start gap-2">
              <LayoutDashboard className="size-4" />
              Дашборды
            </TabsTrigger>
            <TabsTrigger value="events" className="justify-start gap-2">
              <Search className="size-4" />
              События
            </TabsTrigger>
            <TabsTrigger value="flags" className="justify-start gap-2">
              <Settings2 className="size-4" />
              Флаги
            </TabsTrigger>
            <TabsTrigger value="experiments" className="justify-start gap-2">
              <Gauge className="size-4" />
              Эксперименты
            </TabsTrigger>
            <TabsTrigger value="ml" className="justify-start gap-2">
              <Database className="size-4" />
              ML
            </TabsTrigger>
            <TabsTrigger value="llm-poi" className="justify-start gap-2">
              <Sparkles className="size-4" />
              LLM POI
            </TabsTrigger>
            <TabsTrigger value="llm-reviews" className="justify-start gap-2">
              <Shield className="size-4" />
              LLM проверки
            </TabsTrigger>
            <TabsTrigger value="llm-destinations" className="justify-start gap-2">
              <MapPin className="size-4" />
              LLM направления
            </TabsTrigger>
            <TabsTrigger value="debug" className="justify-start gap-2">
              <Activity className="size-4" />
              Debug
            </TabsTrigger>
          </TabsList>
          <div className="mt-4 rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
            Desktop console. Минимальная ширина рассчитана на рабочий монитор, не на мобильный flow.
          </div>
        </aside>

        <section className="min-w-0">
          <TabsContent value="dashboards" className="mt-0 space-y-5">
            <div className="grid gap-3 md:grid-cols-3">
              <Card className="rounded-lg">
                <CardHeader className="p-4">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Sparkles className="size-4" />
                    Пользователи
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0 text-3xl font-semibold tabular-nums">
                  {summary?.product.active_users ?? 0}
                </CardContent>
              </Card>
              <Card className="rounded-lg">
                <CardHeader className="p-4">
                  <CardTitle className="text-sm">Сессии</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0 text-3xl font-semibold tabular-nums">
                  {summary?.product.active_sessions ?? 0}
                </CardContent>
              </Card>
              <Card className="rounded-lg">
                <CardHeader className="p-4">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <TriangleAlert className="size-4" />
                    Ошибки API
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0 text-3xl font-semibold tabular-nums">
                  {summary?.operational.counts.failed_api_request ?? 0}
                </CardContent>
              </Card>
            </div>

            <Card className="rounded-lg border-primary/20 bg-background">
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <LockKeyhole className="size-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-medium">Grafana</div>
                    <div className="truncate text-sm text-muted-foreground">
                      Triply Analytics · отдельный вход
                    </div>
                  </div>
                </div>
                <Button variant="outline" className="shrink-0" onClick={openGrafanaDashboard}>
                  <ExternalLink className="size-4" />
                  Открыть
                </Button>
              </CardContent>
            </Card>

            {summary && (
              <>
                <div className="grid gap-4 2xl:grid-cols-[1.45fr_1fr]">
                  <LineChart
                    title="Events, users, sessions · 14 days"
                    data={summary.charts.daily_events}
                    series={[
                      { key: 'events', label: 'events', color: '#2563eb' },
                      { key: 'users', label: 'users', color: '#16a34a' },
                      { key: 'sessions', label: 'sessions', color: '#f59e0b' },
                    ]}
                  />
                  <BarList
                    title="Top event types"
                    items={summary.charts.top_events.map((item) => ({
                      label: item.event_type,
                      value: item.count,
                    }))}
                  />
                </div>
                <div className="grid gap-4 xl:grid-cols-2">
                  <FunnelChart
                    title="Recommendation funnel"
                    rows={summary.charts.recommendation_funnel}
                  />
                  <FunnelChart title="Itinerary funnel" rows={summary.charts.itinerary_funnel} />
                </div>
                <LineChart
                  title="Operational incidents · 14 days"
                  data={summary.charts.operational_daily}
                  series={[
                    { key: 'failed', label: 'failed API', color: '#dc2626' },
                    { key: 'slow', label: 'slow API', color: '#ea580c' },
                    { key: 'frontend_errors', label: 'frontend errors', color: '#7c3aed' },
                  ]}
                />
                <MetricGrid title="Product" counts={summary.product.counts} />
                <MetricGrid title="ML quality" counts={summary.ml.counts} />
                <MetricGrid title="Operations" counts={summary.operational.counts} />
              </>
            )}
          </TabsContent>

          <TabsContent value="events" className="mt-0 space-y-5">
            <Card className="rounded-lg">
              <CardHeader className="gap-3 p-4">
                <CardTitle>Events explorer</CardTitle>
                <div className="grid gap-2 md:grid-cols-4">
                  <Input
                    value={eventFilters.eventType ?? ''}
                    onChange={(event) =>
                      setEventFilters((prev) => ({ ...prev, eventType: event.target.value }))
                    }
                    placeholder="event_type"
                  />
                  <Input
                    value={eventFilters.userId ?? ''}
                    onChange={(event) =>
                      setEventFilters((prev) => ({ ...prev, userId: event.target.value }))
                    }
                    placeholder="user_id"
                  />
                  <Input
                    value={eventFilters.sessionId ?? ''}
                    onChange={(event) =>
                      setEventFilters((prev) => ({ ...prev, sessionId: event.target.value }))
                    }
                    placeholder="session_id"
                  />
                  <Input
                    value={eventFilters.entityId ?? ''}
                    onChange={(event) =>
                      setEventFilters((prev) => ({ ...prev, entityId: event.target.value }))
                    }
                    placeholder="entity_id"
                  />
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                {recentEvents.map((event) => (
                  <EventRow key={event.id} event={event} />
                ))}
              </CardContent>
            </Card>

            <Card className="rounded-lg">
              <CardHeader className="p-4">
                <CardTitle>User/session timeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 p-4 pt-0">
                {(timelineQuery.data?.sessions ?? []).map((session) => (
                  <div key={session.session_id} className="rounded-lg border p-3">
                    <div className="mb-2 text-xs font-medium text-muted-foreground">
                      {session.session_id}
                    </div>
                    {session.events.map((event) => (
                      <div key={event.id} className="flex gap-3 border-t py-2 text-sm">
                        <span className="w-40 shrink-0 text-xs text-muted-foreground">
                          {formatDate(event.created_at)}
                        </span>
                        <span>{event.event_type}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="flags" className="mt-0 space-y-4">
            {(flagsQuery.data ?? []).map((flag) => (
              <Card key={flag.key} className="rounded-lg">
                <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_120px_140px_auto] md:items-center">
                  <div>
                    <div className="font-medium">{flag.key}</div>
                    <div className="text-xs text-muted-foreground">
                      {flag.description ?? flag.environment}
                    </div>
                  </div>
                  <Badge variant={flag.enabled ? 'default' : 'outline'}>
                    {flag.enabled ? 'enabled' : 'disabled'}
                  </Badge>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={flag.rollout_percentage}
                    onChange={(event) =>
                      flagMutation.mutate({
                        key: flag.key,
                        enabled: flag.enabled,
                        rollout_percentage: Number(event.target.value),
                      })
                    }
                  />
                  <Button
                    variant="outline"
                    onClick={() =>
                      flagMutation.mutate({
                        key: flag.key,
                        enabled: !flag.enabled,
                        rollout_percentage: flag.rollout_percentage,
                      })
                    }
                  >
                    <Settings2 className="size-4" />
                    Toggle
                  </Button>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="experiments" className="mt-0 space-y-5">
            <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
              <Card className="rounded-lg">
                <CardHeader className="p-4">
                  <CardTitle>Experiments</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 p-4 pt-0">
                  {(experimentsQuery.data ?? []).map((experiment) => (
                    <button
                      key={experiment.key}
                      className="flex w-full items-center justify-between rounded-md border p-3 text-left text-sm"
                      onClick={() => setSelectedExperiment(experiment.key)}
                    >
                      <span>{experiment.key}</span>
                      <Badge variant={experiment.status === 'active' ? 'default' : 'outline'}>
                        {experiment.status}
                      </Badge>
                    </button>
                  ))}
                </CardContent>
              </Card>
              <Card className="rounded-lg">
                <CardHeader className="p-4">
                  <CardTitle>Variant metrics</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <JsonBlock value={experimentReportQuery.data ?? {}} />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="ml" className="mt-0 space-y-5">
            <div className="grid gap-3 md:grid-cols-3">
              {Object.entries(mlDatasetQuery.data?.readiness ?? {}).map(([key, ready]) => (
                <Card key={key} className="rounded-lg">
                  <CardContent className="p-4">
                    <Badge variant={ready ? 'default' : 'outline'}>
                      {ready ? 'ready' : 'not ready'}
                    </Badge>
                    <div className="mt-3 text-sm font-medium">{formatEventName(key)}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Card className="rounded-lg">
              <CardHeader className="gap-3 p-4 md:flex-row md:items-center md:justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Database className="size-4" />
                  ML dataset report
                </CardTitle>
                <Button
                  variant="outline"
                  onClick={() => snapshotMutation.mutate()}
                  disabled={snapshotMutation.isPending}
                >
                  <Database className="size-4" />
                  Snapshot
                </Button>
              </CardHeader>
              <CardContent className="grid gap-4 p-4 pt-0 lg:grid-cols-3">
                <JsonBlock value={mlDatasetQuery.data?.ranker ?? {}} />
                <JsonBlock value={mlDatasetQuery.data?.budget ?? {}} />
                <JsonBlock value={mlDatasetQuery.data?.itinerary ?? {}} />
              </CardContent>
            </Card>
            <Card className="rounded-lg">
              <CardHeader className="p-4">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="size-4" />
                  Model registry
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 p-4 pt-0">
                {(modelsQuery.data?.models ?? []).map((model) => (
                  <div
                    key={model.id}
                    className="grid gap-3 rounded-lg border p-3 text-sm md:grid-cols-[1fr_auto]"
                  >
                    <div>
                      <div className="font-medium">
                        {model.name} / {model.version}
                      </div>
                      <div className="text-xs text-muted-foreground">{model.model_type}</div>
                    </div>
                    <Badge variant={model.is_active ? 'default' : 'outline'}>
                      {model.is_active ? 'active' : 'inactive'}
                    </Badge>
                    <div className="md:col-span-2">
                      <JsonBlock value={model.metrics} maxHeight="max-h-36" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="llm-poi" className="mt-0 space-y-4">
            <Card className="rounded-lg">
              <CardHeader className="flex-row items-center justify-between p-4">
                <div>
                  <CardTitle className="text-base">LLM POI candidates</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Предложенные ИИ места не попадают в каталог без approval.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => llmCandidatesQuery.refetch()}
                  disabled={llmCandidatesQuery.isFetching}
                >
                  <RefreshCw className="size-4" />
                  Обновить
                </Button>
              </CardHeader>
            </Card>
            {(llmCandidatesQuery.data?.items ?? []).map((candidate) => (
              <CandidatePOICard
                key={candidate.id}
                candidate={candidate}
                isBusy={candidateActionMutation.isPending}
                onApprove={(id, payload) => candidateActionMutation.mutate({ id, action: 'approve', payload })}
                onReject={(id) => candidateActionMutation.mutate({ id, action: 'reject' })}
                onNeedsData={(id) => candidateActionMutation.mutate({ id, action: 'needs_data' })}
              />
            ))}
            {llmCandidatesQuery.data?.items.length === 0 && (
              <Card className="rounded-lg">
                <CardContent className="p-6 text-sm text-muted-foreground">
                  Кандидатов пока нет.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="llm-reviews" className="mt-0 space-y-4">
            <Card className="rounded-lg">
              <CardHeader className="flex-row items-center justify-between p-4">
                <div>
                  <CardTitle className="text-base">LLM review logs</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Статусы, задержки и issue codes без raw prompt и пользовательских заметок.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => llmReviewLogsQuery.refetch()}
                  disabled={llmReviewLogsQuery.isFetching}
                >
                  <RefreshCw className="size-4" />
                  Обновить
                </Button>
              </CardHeader>
            </Card>
            <div className="space-y-2">
              {(llmReviewLogsQuery.data?.items ?? []).map((log) => (
                <ReviewLogRow key={log.id} log={log} />
              ))}
            </div>
            {llmReviewLogsQuery.data?.items.length === 0 && (
              <Card className="rounded-lg">
                <CardContent className="p-6 text-sm text-muted-foreground">
                  Логов проверок пока нет.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="llm-destinations" className="mt-0 space-y-4">
            <Card className="rounded-lg">
              <CardHeader className="flex-row items-center justify-between p-4">
                <div>
                  <CardTitle className="text-base">Кандидаты направлений LLM</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Новые направления не попадают в каталог автоматически; approval только помечает
                    их для seed/ETL review.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => llmDestinationCandidatesQuery.refetch()}
                  disabled={llmDestinationCandidatesQuery.isFetching}
                >
                  <RefreshCw className="size-4" />
                  Обновить
                </Button>
              </CardHeader>
            </Card>
            {(llmDestinationCandidatesQuery.data?.items ?? []).map((candidate) => (
              <CandidateDestinationCard
                key={candidate.id}
                candidate={candidate}
                isBusy={candidateDestinationActionMutation.isPending}
                onApprove={(id, payload) =>
                  candidateDestinationActionMutation.mutate({ id, action: 'approve', payload })
                }
                onReject={(id) =>
                  candidateDestinationActionMutation.mutate({ id, action: 'reject' })
                }
                onNeedsData={(id) =>
                  candidateDestinationActionMutation.mutate({ id, action: 'needs_data' })
                }
              />
            ))}
            {llmDestinationCandidatesQuery.data?.items.length === 0 && (
              <Card className="rounded-lg">
                <CardContent className="p-6 text-sm text-muted-foreground">
                  Кандидатов направлений пока нет.
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="debug" className="mt-0 space-y-5">
            <DiagnosticsCard
              title="Recommendation debug"
              value={recommendationId}
              onChange={setRecommendationId}
              onSearch={() => setActiveRecommendationId(recommendationId)}
            >
              <JsonBlock value={recommendationDebugQuery.data ?? {}} />
            </DiagnosticsCard>
            <DiagnosticsCard
              title="Budget debug by trip"
              value={budgetTripId}
              onChange={setBudgetTripId}
              onSearch={() => setActiveBudgetTripId(budgetTripId)}
            >
              <JsonBlock value={budgetDebugQuery.data ?? {}} />
            </DiagnosticsCard>
            <DiagnosticsCard
              title="Itinerary debug by trip"
              value={itineraryTripId}
              onChange={setItineraryTripId}
              onSearch={() => setActiveItineraryTripId(itineraryTripId)}
            >
              <JsonBlock value={itineraryDebugQuery.data ?? {}} />
            </DiagnosticsCard>
          </TabsContent>
        </section>
      </Tabs>
    </main>
  );
};
