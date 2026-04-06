const EAQI_TIERS = [
  { label: 'Gut',             color: '#50F0E6' },
  { label: 'Mäßig',          color: '#50CCAA' },
  { label: 'Befriedigend',   color: '#F0E641' },
  { label: 'Schlecht',       color: '#FF5050' },
  { label: 'Sehr schlecht',  color: '#960032' },
  { label: 'Extrem schlecht', color: '#7D2181' },
] as const;

export default function AQILegend() {
  return (
    <div className="px-4">
      <p className="text-[12px] font-normal text-muted-foreground mb-2">Luftqualität (EEA EAQI)</p>
      <div className="flex rounded overflow-hidden h-4 mb-1">
        {EAQI_TIERS.map(({ label, color }) => (
          <div key={label} className="flex-1" style={{ background: color }} />
        ))}
      </div>
      <div className="flex justify-between">
        {EAQI_TIERS.map(({ label, color }) => (
          <span key={label} className="text-[9px] text-muted-foreground leading-tight">{label}</span>
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground mt-1 opacity-60">Quelle: EEA EAQI</p>
    </div>
  );
}
