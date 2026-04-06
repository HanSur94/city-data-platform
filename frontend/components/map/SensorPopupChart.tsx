'use client';
import { useMemo } from 'react';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useTimeseries } from '@/hooks/useTimeseries';

interface SensorPopupChartProps {
  featureId: string;
  town: string;
}

/**
 * Compact 24h time-series chart for a single air quality sensor,
 * shown inside a map popup when a sensor dot is clicked (REQ-AIR-05).
 */
export default function SensorPopupChart({ featureId, town }: SensorPopupChartProps) {
  const now = useMemo(() => new Date(), []);
  const dayAgo = useMemo(() => {
    const d = new Date(now);
    d.setHours(d.getHours() - 24);
    return d;
  }, [now]);

  const { data, loading, error } = useTimeseries('air_quality', dayAgo, now, town);

  // Filter to just this sensor's readings
  const chartData = useMemo(() => {
    if (!data?.points) return [];
    return data.points
      .filter(p => String(p.feature_id ?? '') === featureId)
      .map(p => ({
        time: p.time,
        pm25: typeof p.values.pm25 === 'number' ? p.values.pm25 : null,
        pm10: typeof p.values.pm10 === 'number' ? p.values.pm10 : null,
      }));
  }, [data, featureId]);

  if (loading) {
    return <div className="h-[100px] w-full rounded bg-secondary animate-pulse mt-2" />;
  }

  if (error || chartData.length === 0) {
    return null; // Silently hide chart if no timeseries data available
  }

  const config = {
    pm25: { label: 'PM2.5', color: 'var(--chart-2)' },
    pm10: { label: 'PM10', color: 'var(--chart-4)' },
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
          <YAxis width={25} tick={{ fontSize: 9 }} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(label) => format(new Date(label), 'dd.MM HH:mm')}
              />
            }
          />
          <Line dataKey="pm25" stroke="var(--color-pm25)" dot={false} isAnimationActive={false} strokeWidth={1.5} />
          <Line dataKey="pm10" stroke="var(--color-pm10)" dot={false} isAnimationActive={false} strokeWidth={1.5} />
        </LineChart>
      </ChartContainer>
    </div>
  );
}
