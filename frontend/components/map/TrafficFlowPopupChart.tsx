'use client';
import { useMemo } from 'react';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useTimeseries } from '@/hooks/useTimeseries';

interface TrafficFlowPopupChartProps {
  featureId: string;
  town: string;
  freeflowKmh: number | null;
}

/**
 * Compact 24h time-series chart for a single TomTom traffic flow segment,
 * shown inside a map popup when a road segment is clicked.
 * Shows dual lines: speed (blue) and computed congestion ratio (orange).
 */
export default function TrafficFlowPopupChart({ featureId, town, freeflowKmh }: TrafficFlowPopupChartProps) {
  const now = useMemo(() => new Date(), []);
  const dayAgo = useMemo(() => {
    const d = new Date(now);
    d.setHours(d.getHours() - 24);
    return d;
  }, [now]);

  const { data, loading, error } = useTimeseries('traffic', dayAgo, now, town);

  // Filter to just this segment's readings and compute congestion ratio client-side
  const chartData = useMemo(() => {
    if (!data?.points) return [];
    return data.points
      .filter(p => String(p.feature_id ?? '') === featureId)
      .map(p => {
        const speed = typeof p.values.speed_avg_kmh === 'number' ? p.values.speed_avg_kmh : null;
        let congestion: number | null = null;
        if (freeflowKmh != null && freeflowKmh > 0 && speed != null) {
          congestion = Math.max(0, Math.min(1, 1 - speed / freeflowKmh));
        }
        return {
          time: p.time,
          speed,
          congestion,
        };
      });
  }, [data, featureId, freeflowKmh]);

  if (loading) {
    return <div className="h-[100px] w-full rounded bg-secondary animate-pulse mt-2" />;
  }

  if (error || chartData.length === 0) {
    return null; // Silently hide chart if no timeseries data available
  }

  const hasCongestion = freeflowKmh != null && freeflowKmh > 0;

  const config = {
    speed: { label: 'Geschwindigkeit (km/h)', color: 'var(--chart-1)' },
    congestion: { label: 'Staugrad', color: 'var(--chart-3)' },
  };

  return (
    <div className="mt-2 border-t pt-2">
      <p className="text-[10px] text-muted-foreground mb-1">Letzte 24h</p>
      <ChartContainer config={config} className="h-[100px] w-full">
        <LineChart data={chartData as Record<string, unknown>[]}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            tickFormatter={(v) => format(new Date(v), 'HH:mm')}
            tick={{ fontSize: 9 }}
          />
          <YAxis yAxisId="left" width={25} tick={{ fontSize: 9 }} />
          {hasCongestion && (
            <YAxis yAxisId="right" orientation="right" domain={[0, 1]} width={25} tick={{ fontSize: 9 }} />
          )}
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(label) => format(new Date(label), 'dd.MM HH:mm')}
              />
            }
          />
          <Line
            yAxisId="left"
            dataKey="speed"
            stroke="var(--color-speed)"
            dot={false}
            isAnimationActive={false}
            strokeWidth={1.5}
          />
          {hasCongestion && (
            <Line
              yAxisId="right"
              dataKey="congestion"
              stroke="var(--color-congestion)"
              dot={false}
              isAnimationActive={false}
              strokeWidth={1.5}
            />
          )}
        </LineChart>
      </ChartContainer>
    </div>
  );
}
