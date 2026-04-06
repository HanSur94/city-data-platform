'use client'

interface StalenessBarProps {
  status: 'green' | 'yellow' | 'red' | 'never_fetched'
}

const STATUS_CONFIG = {
  green: {
    bg: 'bg-emerald-500',
    text: 'OK',
  },
  yellow: {
    bg: 'bg-amber-500',
    text: 'Verzoegert',
  },
  red: {
    bg: 'bg-red-500',
    text: 'Ausgefallen',
  },
  never_fetched: {
    bg: 'bg-slate-400',
    text: 'Nie abgerufen',
  },
} as const

export function StalenessBar({ status }: StalenessBarProps) {
  const config = STATUS_CONFIG[status]
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white ${config.bg}`}
    >
      {config.text}
    </span>
  )
}
