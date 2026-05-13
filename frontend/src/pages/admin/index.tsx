import {
  createMLDatasetSnapshot,
  getAdminEvents,
  getBudgetDebug,
  getDashboardSummary,
  getExperimentReport,
  getExperiments,
  getFeatureFlags,
  getItineraryDebug,
  getMLDatasetReport,
  getModelRegistry,
  getRecommendationDebug,
  getTimeline,
  updateFeatureFlag,
  type AdminEvent,
  type EventsFilters,
} from './api';
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
  Database,
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

const formatEventName = (value: string) => value.split('_').join(' ');
const formatDate = (value?: string | null) => value?.slice(0, 19).replace('T', ' ') ?? '-';

const JsonBlock = ({ value, maxHeight = 'max-h-56' }: { value: unknown; maxHeight?: string }) => (
  <pre className={`${maxHeight} overflow-auto rounded-md bg-muted/60 p-3 text-xs`}>
    {JSON.stringify(value ?? {}, null, 2)}
  </pre>
);

const MetricGrid = ({ title, counts }: { title: string; counts: Record<string, number> }) => (
  <section className="space-y-3">
    <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">{title}</h2>
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
        <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder="id" className="h-10 md:w-72" />
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
  const mlDatasetQuery = useQuery({ queryKey: ['admin-ml-dataset-report'], queryFn: getMLDatasetReport });
  const modelsQuery = useQuery({ queryKey: ['admin-model-registry'], queryFn: getModelRegistry });
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

  const summary = summaryQuery.data;
  const recentEvents = useMemo(() => eventsQuery.data?.events ?? summary?.recent_events ?? [], [eventsQuery.data, summary]);

  if (summaryQuery.error) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Card className="rounded-lg border-destructive/40">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 text-destructive">
              <Shield className="size-5" />
              <div className="font-medium">Нет доступа к админ-панели</div>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Проверьте, что ваш user id добавлен в ADMIN_USER_IDS.</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Signal className="size-4" />
            Triply intelligence
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Админ-консоль</h1>
        </div>
        <Button variant="outline" onClick={() => summaryQuery.refetch()} disabled={summaryQuery.isFetching}>
          <RefreshCw className="size-4" />
          Обновить
        </Button>
      </header>

      <Tabs defaultValue="dashboards" className="space-y-5">
        <TabsList className="flex h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="dashboards">Дашборды</TabsTrigger>
          <TabsTrigger value="events">События</TabsTrigger>
          <TabsTrigger value="flags">Флаги</TabsTrigger>
          <TabsTrigger value="experiments">Эксперименты</TabsTrigger>
          <TabsTrigger value="ml">ML</TabsTrigger>
          <TabsTrigger value="debug">Debug</TabsTrigger>
        </TabsList>

        <TabsContent value="dashboards" className="space-y-5">
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

          {summary && (
            <>
              <MetricGrid title="Product" counts={summary.product.counts} />
              <MetricGrid title="ML quality" counts={summary.ml.counts} />
              <MetricGrid title="Operations" counts={summary.operational.counts} />
            </>
          )}
        </TabsContent>

        <TabsContent value="events" className="space-y-5">
          <Card className="rounded-lg">
            <CardHeader className="gap-3 p-4">
              <CardTitle>Events explorer</CardTitle>
              <div className="grid gap-2 md:grid-cols-4">
                <Input
                  value={eventFilters.eventType ?? ''}
                  onChange={(event) => setEventFilters((prev) => ({ ...prev, eventType: event.target.value }))}
                  placeholder="event_type"
                />
                <Input
                  value={eventFilters.userId ?? ''}
                  onChange={(event) => setEventFilters((prev) => ({ ...prev, userId: event.target.value }))}
                  placeholder="user_id"
                />
                <Input
                  value={eventFilters.sessionId ?? ''}
                  onChange={(event) => setEventFilters((prev) => ({ ...prev, sessionId: event.target.value }))}
                  placeholder="session_id"
                />
                <Input
                  value={eventFilters.entityId ?? ''}
                  onChange={(event) => setEventFilters((prev) => ({ ...prev, entityId: event.target.value }))}
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
                  <div className="mb-2 text-xs font-medium text-muted-foreground">{session.session_id}</div>
                  {session.events.map((event) => (
                    <div key={event.id} className="flex gap-3 border-t py-2 text-sm">
                      <span className="w-40 shrink-0 text-xs text-muted-foreground">{formatDate(event.created_at)}</span>
                      <span>{event.event_type}</span>
                    </div>
                  ))}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="flags" className="space-y-4">
          {(flagsQuery.data ?? []).map((flag) => (
            <Card key={flag.key} className="rounded-lg">
              <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_120px_140px_auto] md:items-center">
                <div>
                  <div className="font-medium">{flag.key}</div>
                  <div className="text-xs text-muted-foreground">{flag.description ?? flag.environment}</div>
                </div>
                <Badge variant={flag.enabled ? 'default' : 'outline'}>{flag.enabled ? 'enabled' : 'disabled'}</Badge>
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

        <TabsContent value="experiments" className="space-y-5">
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
                    <Badge variant={experiment.status === 'active' ? 'default' : 'outline'}>{experiment.status}</Badge>
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

        <TabsContent value="ml" className="space-y-5">
          <div className="grid gap-3 md:grid-cols-3">
            {Object.entries(mlDatasetQuery.data?.readiness ?? {}).map(([key, ready]) => (
              <Card key={key} className="rounded-lg">
                <CardContent className="p-4">
                  <Badge variant={ready ? 'default' : 'outline'}>{ready ? 'ready' : 'not ready'}</Badge>
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
              <Button variant="outline" onClick={() => snapshotMutation.mutate()} disabled={snapshotMutation.isPending}>
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
                <div key={model.id} className="grid gap-3 rounded-lg border p-3 text-sm md:grid-cols-[1fr_auto]">
                  <div>
                    <div className="font-medium">
                      {model.name} / {model.version}
                    </div>
                    <div className="text-xs text-muted-foreground">{model.model_type}</div>
                  </div>
                  <Badge variant={model.is_active ? 'default' : 'outline'}>{model.is_active ? 'active' : 'inactive'}</Badge>
                  <div className="md:col-span-2">
                    <JsonBlock value={model.metrics} maxHeight="max-h-36" />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="debug" className="space-y-5">
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
      </Tabs>
    </main>
  );
};
