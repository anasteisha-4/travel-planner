import { getAdminEvents, getDashboardSummary, type AdminEvent } from './api';
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/shared/ui';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Search, Shield, Signal, Sparkles, TriangleAlert } from 'lucide-react';
import { useMemo, useState } from 'react';

const formatEventName = (value: string) => value.split('_').join(' ');

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
  <div className="grid gap-2 border-b py-3 text-sm md:grid-cols-[180px_1fr_160px]">
    <div>
      <div className="font-medium">{event.event_type}</div>
      <div className="text-xs text-muted-foreground">{event.created_at?.slice(0, 19).replace('T', ' ')}</div>
    </div>
    <pre className="max-h-28 overflow-auto rounded-md bg-muted/60 p-3 text-xs">
      {JSON.stringify(event.context, null, 2)}
    </pre>
    <div className="min-w-0 text-xs text-muted-foreground">
      <div className="truncate">user: {event.user_id ?? 'anonymous'}</div>
      <div className="truncate">entity: {event.entity_id ?? '-'}</div>
      <div className="truncate">session: {event.session_id}</div>
    </div>
  </div>
);

export const AdminPage = () => {
  const [eventFilter, setEventFilter] = useState('');
  const summaryQuery = useQuery({
    queryKey: ['admin-dashboard-summary'],
    queryFn: getDashboardSummary,
  });
  const eventsQuery = useQuery({
    queryKey: ['admin-events', eventFilter],
    queryFn: () => getAdminEvents(eventFilter),
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
          <h1 className="mt-2 text-3xl font-semibold tracking-normal">Админ-дашборды</h1>
        </div>
        <Button variant="outline" onClick={() => summaryQuery.refetch()} disabled={summaryQuery.isFetching}>
          <RefreshCw className="size-4" />
          Обновить
        </Button>
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        <Card className="rounded-lg">
          <CardHeader className="p-4">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Sparkles className="size-4" />
              Пользователи
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-3xl font-semibold tabular-nums">{summary?.product.active_users ?? 0}</CardContent>
        </Card>
        <Card className="rounded-lg">
          <CardHeader className="p-4">
            <CardTitle className="text-sm">Сессии</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-3xl font-semibold tabular-nums">{summary?.product.active_sessions ?? 0}</CardContent>
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

      <Card className="rounded-lg">
        <CardHeader className="gap-3 p-4 md:flex-row md:items-center md:justify-between">
          <CardTitle>Events explorer</CardTitle>
          <div className="flex items-center gap-2">
            <Search className="size-4 text-muted-foreground" />
            <Input
              value={eventFilter}
              onChange={(event) => setEventFilter(event.target.value)}
              placeholder="event_type"
              className="h-10 w-56"
            />
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {recentEvents.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </CardContent>
      </Card>
    </main>
  );
};
