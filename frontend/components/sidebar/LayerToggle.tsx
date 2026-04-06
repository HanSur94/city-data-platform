'use client';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';
import { DataTypeBadge } from '@/components/ui/DataTypeBadge';
import { Info, AlertTriangle } from 'lucide-react';
import type { DataType, LayerMetadataEntry } from '@/lib/layer-metadata';

interface LayerToggleProps {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  freshnessError?: boolean;
  layerKey?: string;
  dataType?: DataType;
  isStale?: boolean;
  metadata?: LayerMetadataEntry;
  lastUpdated?: string | null;
}

function formatInterval(seconds: number | null): string {
  if (seconds == null) return 'einmalig';
  if (seconds < 60) return `alle ${seconds} Sek`;
  if (seconds < 3600) return `alle ${Math.round(seconds / 60)} Min`;
  if (seconds < 86400) return `alle ${Math.round(seconds / 3600)} Std`;
  return `alle ${Math.round(seconds / 86400)} Tage`;
}

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return 'Keine Daten';
  try {
    const d = new Date(ts);
    return d.toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts;
  }
}

export default function LayerToggle({
  id,
  label,
  checked,
  onCheckedChange,
  freshnessError,
  layerKey,
  dataType,
  isStale,
  metadata,
  lastUpdated,
}: LayerToggleProps) {
  return (
    <div className="flex items-center justify-between min-h-[44px] px-4 hover:bg-[#f4f5f7] rounded-md">
      <Label htmlFor={id} className="text-[12px] font-normal leading-[1.4] cursor-pointer flex items-center gap-2">
        {freshnessError && <span className="inline-block w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />}
        {isStale && (
          <AlertTriangle
            size={12}
            className="text-orange-500 flex-shrink-0"
            title="Daten moeglicherweise veraltet"
          />
        )}
        {label}
        {dataType && <DataTypeBadge dataType={dataType} size="sm" />}
      </Label>
      <div className="flex items-center gap-1.5">
        {metadata && (
          <Popover>
            <PopoverTrigger
              render={<button type="button" aria-label="Metadaten anzeigen" />}
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
              className="p-0.5 rounded hover:bg-slate-100"
            >
              <Info size={14} className="text-muted-foreground" />
            </PopoverTrigger>
            <PopoverContent side="right" className="w-64 text-[12px] space-y-1.5 p-3">
              <div>
                <span className="text-muted-foreground">Quelle: </span>
                <a
                  href={metadata.sourceUrl}
                  target="_blank"
                  rel="noopener"
                  className="text-blue-600 underline"
                >
                  {metadata.sourceName}
                </a>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">Typ:</span>
                <DataTypeBadge dataType={metadata.dataType} size="sm" />
              </div>
              <div>
                <span className="text-muted-foreground">Aktualisierung: </span>
                <span>{formatInterval(metadata.updateIntervalSeconds)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Lizenz: </span>
                <a
                  href={metadata.licenseUrl}
                  target="_blank"
                  rel="noopener"
                  className="text-blue-600 underline"
                >
                  {metadata.license}
                </a>
              </div>
              <div>
                <span className="text-muted-foreground">Letztes Update: </span>
                <span>{formatTimestamp(lastUpdated)}</span>
              </div>
            </PopoverContent>
          </Popover>
        )}
        <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
      </div>
    </div>
  );
}
