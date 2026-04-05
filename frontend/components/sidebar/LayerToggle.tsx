'use client';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface LayerToggleProps {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  freshnessError?: boolean;
}

export default function LayerToggle({ id, label, checked, onCheckedChange, freshnessError }: LayerToggleProps) {
  return (
    <div className="flex items-center justify-between min-h-[44px] px-4 hover:bg-[#f4f5f7] rounded-md">
      <Label htmlFor={id} className="text-[12px] font-normal leading-[1.4] cursor-pointer flex items-center gap-2">
        {freshnessError && <span className="inline-block w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />}
        {label}
      </Label>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}
