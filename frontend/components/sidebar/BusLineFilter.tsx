'use client';
import { lineColor } from '@/components/map/BusPositionLayer';

interface BusLineFilterProps {
  lines: string[];
  hiddenLines: Set<string>;
  onToggle: (line: string) => void;
}

export default function BusLineFilter({ lines, hiddenLines, onToggle }: BusLineFilterProps) {
  if (lines.length === 0) return null;

  const sorted = [...lines].sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true })
  );

  const allVisible = hiddenLines.size === 0;
  const allHidden = hiddenLines.size === lines.length;

  const handleToggleAll = () => {
    if (allHidden) {
      // Show all: remove all from hidden by toggling each hidden one
      lines.forEach((l) => {
        if (hiddenLines.has(l)) onToggle(l);
      });
    } else {
      // Hide all: add all visible ones to hidden
      lines.forEach((l) => {
        if (!hiddenLines.has(l)) onToggle(l);
      });
    }
  };

  return (
    <div className="px-4 pb-2">
      <div className="max-h-[200px] overflow-y-auto border border-slate-100 rounded bg-slate-50">
        {/* Toggle all row */}
        <button
          onClick={handleToggleAll}
          className="w-full text-left px-3 py-1.5 text-[11px] text-slate-500 hover:bg-slate-100 border-b border-slate-100 font-medium"
        >
          {allHidden ? 'Alle anzeigen' : 'Alle ausblenden'}
        </button>

        {/* Per-line rows */}
        {sorted.map((name) => {
          const visible = !hiddenLines.has(name);
          return (
            <label
              key={name}
              className="flex items-center gap-2 px-3 py-1 cursor-pointer hover:bg-slate-100"
            >
              <input
                type="checkbox"
                checked={visible}
                onChange={() => onToggle(name)}
                className="accent-primary h-3 w-3 flex-shrink-0"
              />
              <span
                className="inline-block w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: lineColor(name) }}
              />
              <span className="text-[12px] text-slate-700 truncate">{name}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
