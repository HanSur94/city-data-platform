'use client'
import { useState, useRef, useCallback } from 'react'
import { format } from 'date-fns'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'

// 24h window split into 15-min steps
// step 0 = 24h ago, step 96 = live (now)
const SLIDER_STEPS = 24 * 4 // 96

function timestampAt(step: number): Date {
  const msPerStep = 15 * 60 * 1000
  return new Date(Date.now() - (SLIDER_STEPS - step) * msPerStep)
}

interface TimeSliderProps {
  // null = live (rightmost), Date = historical timestamp
  value: Date | null
  onChange: (ts: Date | null) => void
}

export function TimeSlider({ value, onChange }: TimeSliderProps) {
  // Convert external value back to slider step for controlled rendering
  function dateToStep(d: Date | null): number {
    if (!d) return SLIDER_STEPS
    const msPerStep = 15 * 60 * 1000
    const stepsAgo = Math.round((Date.now() - d.getTime()) / msPerStep)
    return Math.max(0, Math.min(SLIDER_STEPS, SLIDER_STEPS - stepsAgo))
  }

  const [displayStep, setDisplayStep] = useState(() => dateToStep(value))
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isLive = displayStep === SLIDER_STEPS

  const handleChange = useCallback(
    (v: number | readonly number[]) => {
      const step = Array.isArray(v) ? (v as number[])[0] : (v as number)
      setDisplayStep(step)
      // Debounce the external onChange to avoid excessive API calls
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        const ts = step === SLIDER_STEPS ? null : timestampAt(step)
        onChange(ts)
      }, 300)
    },
    [onChange],
  )

  const goLive = useCallback(() => {
    setDisplayStep(SLIDER_STEPS)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    onChange(null)
  }, [onChange])

  return (
    <div className="w-full h-12 flex items-center gap-3 px-4 bg-background border-t">
      <Slider
        min={0}
        max={SLIDER_STEPS}
        step={1}
        value={[displayStep]}
        onValueChange={handleChange}
        className="flex-1"
        aria-label="Zeitliche Navigation"
      />
      <span className="text-[14px] text-muted-foreground whitespace-nowrap min-w-[60px]">
        {isLive ? 'Live' : `${format(timestampAt(displayStep), 'HH:mm')} Uhr`}
      </span>
      {!isLive && (
        <Button size="sm" variant="outline" onClick={goLive}>
          Zurück zu Live
        </Button>
      )}
    </div>
  )
}
