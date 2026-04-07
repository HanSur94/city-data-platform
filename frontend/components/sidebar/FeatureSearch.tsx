'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';

export interface SearchResult {
  id: string;
  semantic_id: string | null;
  domain: string;
  name: string;
  longitude: number;
  latitude: number;
}

interface FeatureSearchProps {
  town: string;
  onSelect: (result: SearchResult) => void;
}

const DOMAIN_BADGES: Record<string, { label: string; color: string }> = {
  transit: { label: 'OEPNV', color: 'bg-blue-100 text-blue-700' },
  air_quality: { label: 'Luft', color: 'bg-green-100 text-green-700' },
  water: { label: 'Wasser', color: 'bg-cyan-100 text-cyan-700' },
  traffic: { label: 'Verkehr', color: 'bg-orange-100 text-orange-700' },
  energy: { label: 'Energie', color: 'bg-yellow-100 text-yellow-700' },
  community: { label: 'Gemeinwesen', color: 'bg-purple-100 text-purple-700' },
  infrastructure: { label: 'Infrastruktur', color: 'bg-red-100 text-red-700' },
  weather: { label: 'Wetter', color: 'bg-sky-100 text-sky-700' },
  demographics: { label: 'Demografie', color: 'bg-pink-100 text-pink-700' },
  buildings: { label: 'Gebaeude', color: 'bg-stone-100 text-stone-700' },
};

export default function FeatureSearch({ town, onSelect }: FeatureSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [noResults, setNoResults] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const blurTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchResults = useCallback(
    async (q: string) => {
      if (q.length < 2) {
        setResults([]);
        setNoResults(false);
        return;
      }
      setLoading(true);
      try {
        const res = await fetch(
          `/api/features/search?q=${encodeURIComponent(q)}&town=${encodeURIComponent(town)}`,
        );
        if (!res.ok) {
          setResults([]);
          setNoResults(true);
          return;
        }
        const data = (await res.json()) as SearchResult[];
        setResults(data);
        setNoResults(data.length === 0);
      } catch {
        setResults([]);
        setNoResults(true);
      } finally {
        setLoading(false);
      }
    },
    [town],
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 2) {
      setResults([]);
      setNoResults(false);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      fetchResults(query);
      setShowDropdown(true);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchResults]);

  const handleSelect = (result: SearchResult) => {
    setQuery('');
    setResults([]);
    setShowDropdown(false);
    setNoResults(false);
    onSelect(result);
  };

  const handleBlur = () => {
    // Small delay so click on result can register before dropdown closes
    blurTimeoutRef.current = setTimeout(() => setShowDropdown(false), 200);
  };

  const handleFocus = () => {
    if (blurTimeoutRef.current) clearTimeout(blurTimeoutRef.current);
    if (results.length > 0 || noResults) setShowDropdown(true);
  };

  return (
    <div className="relative px-4 pb-3">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder="Adresse oder Feature suchen..."
          className="w-full pl-8 pr-3 py-1.5 text-[13px] border border-slate-200 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      {showDropdown && (
        <div className="absolute left-4 right-4 mt-1 bg-white border border-slate-200 rounded-md shadow-lg z-50 max-h-[240px] overflow-y-auto">
          {loading && (
            <p className="px-3 py-2 text-[12px] text-muted-foreground">Suche...</p>
          )}
          {!loading && noResults && (
            <p className="px-3 py-2 text-[12px] text-muted-foreground">Keine Ergebnisse</p>
          )}
          {!loading &&
            results.map((r) => {
              const badge = DOMAIN_BADGES[r.domain] ?? {
                label: r.domain,
                color: 'bg-slate-100 text-slate-600',
              };
              return (
                <button
                  key={r.id}
                  className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2 border-b last:border-b-0 border-slate-100"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSelect(r)}
                >
                  <span className="text-[13px] truncate flex-1">{r.name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap ${badge.color}`}
                  >
                    {badge.label}
                  </span>
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
