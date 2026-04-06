'use client';

import { type DataType, DATA_TYPE_COLORS } from '@/lib/layer-metadata';

interface DataTypeBadgeProps {
  dataType: DataType;
  size?: 'sm' | 'md';
}

export function DataTypeBadge({ dataType, size = 'sm' }: DataTypeBadgeProps) {
  const bgColor = DATA_TYPE_COLORS[dataType];
  const textColor = dataType === 'SCRAPED' ? '#000' : '#fff';
  const fontSize = size === 'sm' ? '10px' : '12px';

  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 font-medium uppercase tracking-wide"
      style={{
        backgroundColor: bgColor,
        color: textColor,
        fontSize,
        lineHeight: '1.4',
      }}
    >
      {dataType}
    </span>
  );
}
