'use client';
import { useRelativeTime } from '@/hooks/useRelativeTime';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';

interface FreshnessIndicatorProps {
  lastFetched: Date | null;
}

function freshnessColor(date: Date | null): string {
  if (!date) return 'bg-gray-400';
  const ageMs = Date.now() - date.getTime();
  const ageMin = ageMs / 60_000;
  if (ageMin < 5)  return 'bg-green-500';
  if (ageMin < 30) return 'bg-yellow-400';
  return 'bg-red-500';
}

export default function FreshnessIndicator({ lastFetched }: FreshnessIndicatorProps) {
  const relative = useRelativeTime(lastFetched);
  const exact = lastFetched
    ? format(lastFetched, 'HH:mm:ss', { locale: de })
    : null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger
          render={
            <div className="flex items-center gap-1 cursor-default" />
          }
        >
          <span className={`inline-block w-2 h-2 rounded-full ${freshnessColor(lastFetched)}`} />
          <span className="text-[12px] text-muted-foreground">
            {relative || 'Keine Daten'}
          </span>
        </TooltipTrigger>
        {exact && (
          <TooltipContent>
            <p>Zuletzt aktualisiert: {exact}</p>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
