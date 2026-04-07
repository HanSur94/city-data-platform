'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useFeatureData } from '@/hooks/useFeatureData';

interface CrossDomainSectionProps {
  featureId: string | null;
  ownDomain: string;
}

const DOMAIN_LABELS: Record<string, string> = {
  transit: 'OEPNV',
  air_quality: 'Luftqualitaet',
  water: 'Gewaesser',
  traffic: 'Verkehr',
  energy: 'Energie',
  community: 'Gemeinwesen',
  infrastructure: 'Infrastruktur',
  weather: 'Wetter',
  demographics: 'Demografie',
  buildings: 'Gebaeude',
};

/**
 * Collapsible section showing cross-domain observations for a feature.
 * Only renders if useFeatureData returns observations in domains OTHER than ownDomain.
 */
export function CrossDomainSection({ featureId, ownDomain }: CrossDomainSectionProps) {
  const { data, loading } = useFeatureData(featureId);
  const [open, setOpen] = useState(false);

  if (!data || loading) return null;

  // Filter observations to only show other domains
  const crossDomainEntries = Object.entries(data.observations).filter(
    ([domain]) => domain !== ownDomain,
  );

  if (crossDomainEntries.length === 0) return null;

  return (
    <div className="mt-2 border-t pt-1.5">
      <button
        className="flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground w-full"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        Weitere Daten ({crossDomainEntries.length})
      </button>
      {open && (
        <div className="mt-1 space-y-1.5">
          {crossDomainEntries.map(([domain, obs]) => (
            <div key={domain} className="text-[11px]">
              <p className="font-medium text-muted-foreground">
                {DOMAIN_LABELS[domain] ?? domain}
              </p>
              {obs.values && (
                <div className="pl-2">
                  {Object.entries(obs.values).slice(0, 5).map(([key, val]) => (
                    <p key={key}>
                      {key}: {String(val)}
                    </p>
                  ))}
                </div>
              )}
              {obs.timestamp && (
                <p className="text-[10px] text-muted-foreground pl-2">
                  {new Date(obs.timestamp).toLocaleString('de-DE')}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
