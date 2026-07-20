import dayjs from 'dayjs';

export function formatDate(date: string | null | undefined): string {
  if (!date) return '—';
  return dayjs(date).format('DD MMM YYYY');
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return '—';
  return dayjs(date).format('DD MMM YYYY HH:mm');
}

export function formatTimeAgo(date: string | null | undefined): string {
  if (!date) return '—';
  const d = dayjs(date);
  const now = dayjs();
  const diffMin = now.diff(d, 'minute');
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = now.diff(d, 'hour');
  if (diffH < 24) return `${diffH}h ago`;
  return `${now.diff(d, 'day')}d ago`;
}

export function formatNumber(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatCurrency(
  val: number | null | undefined,
  currency = 'EUR'
): string {
  if (val === null || val === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(val);
}

export function formatTonnage(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
  return val.toLocaleString();
}

export function formatSpeed(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${val.toFixed(1)} kn`;
}

export function formatCII(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return val.toFixed(3);
}

export function ciiColor(rating: string): string {
  const map: Record<string, string> = {
    A: '#00e676',
    B: '#40c4ff',
    C: '#ffd740',
    D: '#ff6e40',
    E: '#ff1744',
  };
  return map[rating] || '#90a4ae';
}

export function ciiBgColor(rating: string): string {
  const map: Record<string, string> = {
    A: 'rgba(0, 230, 118, 0.15)',
    B: 'rgba(64, 196, 255, 0.15)',
    C: 'rgba(255, 215, 64, 0.15)',
    D: 'rgba(255, 110, 64, 0.15)',
    E: 'rgba(255, 23, 68, 0.15)',
  };
  return map[rating] || 'rgba(144, 164, 174, 0.15)';
}

export function severityColor(severity: string): string {
  const map: Record<string, string> = {
    critical: '#ff1744',
    high: '#ff6e40',
    medium: '#ffd740',
    low: '#40c4ff',
  };
  return map[severity] || '#90a4ae';
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    'in-port': 'In Port',
    'at-sea': 'At Sea',
    'dry-dock': 'Dry Dock',
    idle: 'Idle',
    planned: 'Planned',
    'in-progress': 'In Progress',
    completed: 'Completed',
    cancelled: 'Cancelled',
    active: 'Active',
    pending: 'Pending',
    compliant: 'Compliant',
    'non-compliant': 'Non-Compliant',
  };
  return map[status] || status;
}

export function formatPercentage(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${(val * 100).toFixed(1)}%`;
}

export function formatEmissions(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  if (val >= 1_000) return `${(val / 1_000).toFixed(1)}K tCO₂`;
  return `${val.toFixed(0)} tCO₂`;
}
