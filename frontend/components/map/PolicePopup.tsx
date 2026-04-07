'use client';
import type { Feature } from 'geojson';

interface PolicePopupProps {
  feature: Feature;
}

const CATEGORY_LABELS: Record<string, string> = {
  accident: 'Verkehrsunfall',
  theft: 'Diebstahl/Einbruch',
  fire: 'Brand',
  missing: 'Vermisstensuche',
  fraud: 'Betrug',
  general: 'Polizeimeldung',
};

const CATEGORY_COLORS: Record<string, string> = {
  accident: '#ef4444',
  theft: '#f97316',
  fire: '#dc2626',
  missing: '#8b5cf6',
  fraud: '#eab308',
  general: '#1d4ed8',
};

export default function PolicePopup({ feature }: PolicePopupProps) {
  const props = feature.properties ?? {};
  const title = (props.title as string) ?? 'Polizeimeldung';
  const description = (props.description as string) ?? '';
  const category = (props.category as string) ?? 'general';
  const locationName = props.location_name as string | undefined;
  const pubDate = props.pub_date as string | undefined;
  const link = props.link as string | undefined;

  // Clean title: remove POL-AA: prefix
  const cleanTitle = title.replace(/^POL-[A-Z]{1,4}:\s*/, '');

  // Format date
  let dateStr = '';
  if (pubDate) {
    try {
      const d = new Date(pubDate);
      dateStr = d.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch { /* ignore */ }
  }

  return (
    <div className="text-sm space-y-1.5 max-w-[260px]">
      <div className="flex items-center gap-2">
        <span
          className="text-[11px] px-1.5 py-0.5 rounded text-white"
          style={{ backgroundColor: CATEGORY_COLORS[category] ?? '#1d4ed8' }}
        >
          {CATEGORY_LABELS[category] ?? 'Meldung'}
        </span>
      </div>
      <p className="text-[14px] font-semibold leading-tight">
        {cleanTitle}
      </p>
      {description && (
        <p className="text-[12px] text-muted-foreground line-clamp-3">
          {description}
        </p>
      )}
      {locationName && (
        <p className="text-[12px]">
          Ort: {locationName}
        </p>
      )}
      {dateStr && (
        <p className="text-[11px] text-muted-foreground">
          {dateStr}
        </p>
      )}
      {link && (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] text-blue-600 hover:underline"
        >
          Vollmeldung auf Presseportal
        </a>
      )}
    </div>
  );
}
