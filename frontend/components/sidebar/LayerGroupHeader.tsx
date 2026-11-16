'use client';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import type { GroupSwitchState } from '@/lib/layer-registry';

interface LayerGroupHeaderProps {
  id: string;
  title: string;
  activeCount: number;
  total: number;
  state: GroupSwitchState;
  onToggle: () => void;
  /** Number of layers in the group whose source never delivered data. */
  noDataCount?: number;
  variant?: 'group' | 'master';
}

export default function LayerGroupHeader({
  id,
  title,
  activeCount,
  total,
  state,
  onToggle,
  noDataCount = 0,
  variant = 'group',
}: LayerGroupHeaderProps) {
  const ariaLabel = `${title}: ${activeCount} von ${total} Ebenen aktiv – ${
    state === 'on' ? 'alle ausschalten' : 'alle einschalten'
  }`;

  return (
    <div className="flex items-center justify-between gap-2 min-h-[44px] px-4">
      <div className="min-w-0">
        <Label
          htmlFor={id}
          className={`text-[12px] leading-[1.4] text-muted-foreground uppercase tracking-wide cursor-pointer flex items-baseline gap-2 ${
            variant === 'master' ? 'font-medium' : 'font-normal'
          }`}
        >
          <span className="truncate">{title}</span>
          <span className="text-[11px] normal-case tracking-normal tabular-nums">
            {activeCount} / {total}
          </span>
        </Label>
        {noDataCount > 0 && (
          <p className="text-[11px] leading-[1.4] text-slate-400">{noDataCount} ohne Daten</p>
        )}
      </div>
      <Switch
        id={id}
        checked={state !== 'off'}
        onCheckedChange={() => onToggle()}
        aria-label={ariaLabel}
        className={state === 'mixed' ? 'opacity-60' : undefined}
        {...(state === 'mixed' ? { 'aria-checked': 'mixed' as const } : {})}
      />
    </div>
  );
}
