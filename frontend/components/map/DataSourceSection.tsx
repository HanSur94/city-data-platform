'use client';

import type { DataType } from '@/lib/layer-metadata';
import { DataTypeBadge } from '@/components/ui/DataTypeBadge';

interface DataSourceSectionProps {
  sourceName: string;
  sourceUrl: string;
  dataType: DataType;
  timestamp?: string | null;
}

export function DataSourceSection({
  sourceName,
  sourceUrl,
  dataType,
  timestamp,
}: DataSourceSectionProps) {
  return (
    <div className="border-t pt-2 mt-2">
      <p className="text-muted-foreground" style={{ fontSize: '11px' }}>
        Datenquelle
      </p>
      <div className="flex items-center gap-1.5 mt-0.5">
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener"
          className="text-blue-600 underline"
          style={{ fontSize: '12px' }}
        >
          {sourceName}
        </a>
        <DataTypeBadge dataType={dataType} />
      </div>
      {timestamp && (
        <p className="text-muted-foreground mt-0.5" style={{ fontSize: '11px' }}>
          Stand: {timestamp}
        </p>
      )}
    </div>
  );
}
