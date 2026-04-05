'use client'
import { useState } from 'react'
import { addDays, endOfDay, startOfDay, format } from 'date-fns'
import type { DateRange } from 'react-day-picker'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { Button } from '@/components/ui/button'

interface DateRangeValue {
  from: Date
  to: Date
}

interface DateRangePickerProps {
  value: DateRangeValue
  onChange: (range: DateRangeValue) => void
  maxDays?: number // default 90
}

const PRESETS = [
  { label: '24h', days: 1 },
  { label: '7 Tage', days: 7 },
  { label: '30 Tage', days: 30 },
]

function isActivePreset(value: DateRangeValue, days: number): boolean {
  const expectedFrom = startOfDay(addDays(new Date(), -days))
  return (
    Math.abs(value.from.getTime() - expectedFrom.getTime()) < 60_000 * 60 // within 1h tolerance
  )
}

export function DateRangePicker({ value, onChange, maxDays = 90 }: DateRangePickerProps) {
  const [open, setOpen] = useState(false)
  const [pendingRange, setPendingRange] = useState<DateRange | undefined>({
    from: value.from,
    to: value.to,
  })

  const customRangeLabel = !PRESETS.some(p => isActivePreset(value, p.days))
    ? `${format(value.from, 'dd.MM.yyyy')} – ${format(value.to, 'dd.MM.yyyy')}`
    : 'Zeitraum...'

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {PRESETS.map(p => (
        <Button
          key={p.label}
          size="sm"
          variant={isActivePreset(value, p.days) ? 'default' : 'outline'}
          onClick={() =>
            onChange({
              from: startOfDay(addDays(new Date(), -p.days)),
              to: endOfDay(new Date()),
            })
          }
        >
          {p.label}
        </Button>
      ))}

      <Popover open={open} onOpenChange={(nextOpen) => setOpen(nextOpen)}>
        <PopoverTrigger
          render={
            <button
              className="inline-flex h-7 items-center gap-1 rounded-[min(var(--radius-md),12px)] border border-border bg-background px-2.5 text-[0.8rem] font-medium transition-all hover:bg-muted hover:text-foreground"
            >
              {customRangeLabel}
            </button>
          }
        />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            selected={pendingRange}
            onSelect={setPendingRange}
            numberOfMonths={2}
            disabled={(date) => {
              // Disallow future dates and ranges > maxDays
              if (date > new Date()) return true
              if (pendingRange?.from && !pendingRange.to) {
                const diff = Math.abs(date.getTime() - pendingRange.from.getTime())
                if (diff > maxDays * 24 * 60 * 60 * 1000) return true
              }
              return false
            }}
          />
          <div className="flex gap-2 p-3 border-t">
            <Button
              size="sm"
              onClick={() => {
                if (pendingRange?.from && pendingRange?.to) {
                  onChange({ from: pendingRange.from, to: pendingRange.to })
                  setOpen(false)
                }
              }}
              disabled={!pendingRange?.from || !pendingRange?.to}
            >
              Übernehmen
            </Button>
            <Button size="sm" variant="outline" onClick={() => setOpen(false)}>
              Abbrechen
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
