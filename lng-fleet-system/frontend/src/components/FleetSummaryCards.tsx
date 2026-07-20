import { Grid, Card, CardContent, Typography, Skeleton } from '@mui/material';
import type { DashboardSummary } from '../services/types';
import { formatNumber, formatCurrency } from '../utils/formatters';

interface FleetSummaryCardsProps {
  summary: DashboardSummary | null;
  loading?: boolean;
}

const cards = [
  { key: 'total_vessels', label: 'Total Vessels', format: 'number', color: '#40c4ff' },
  { key: 'active_voyages', label: 'Active Voyages', format: 'number', color: '#00e676' },
  { key: 'fleet_avg_cii', label: 'Fleet Avg CII', format: 'cii', color: '#e0e6f0' },
  { key: 'fleet_cii_coverage_pct', label: 'CII Coverage', format: 'pct', color: '#ffd740' },
  { key: 'open_alerts', label: 'Open Alerts', format: 'number', color: '#ff6e40' },
  { key: 'critical_alerts', label: 'Critical Alerts', format: 'number', color: '#ff1744' },
  { key: 'fleet_fuel_consumption_tonne', label: 'Fuel (tonnes)', format: 'number', color: '#8896b0' },
  { key: 'eu_ets_exposure_eur', label: 'EUA Liability (€)', format: 'currency', color: '#ff1744' },
];

export default function FleetSummaryCards({ summary, loading }: FleetSummaryCardsProps) {
  return (
    <Grid container spacing={2}>
      {cards.map((card) => (
        <Grid item xs={6} sm={4} md={3} key={card.key}>
          <Card
            sx={{
              borderLeft: `3px solid ${card.color}`,
              height: '100%',
            }}
          >
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: '0.65rem' }}>
                {card.label}
              </Typography>
              {loading || !summary ? (
                <Skeleton width="60%" height={36} sx={{ mt: 0.5 }} />
              ) : (
                <Typography variant="h5" sx={{ color: card.color, mt: 0.5, fontFamily: "'JetBrains Mono', monospace" }}>
                  {formatValue(summary, card)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

function formatValue(summary: DashboardSummary, card: typeof cards[0]): string {
  const raw = (summary as any)[card.key];
  if (raw === null || raw === undefined) return '—';
  if (card.format === 'currency') return formatCurrency(raw);
  if (card.format === 'cii') return (raw as number).toFixed(3);
  if (card.format === 'pct') return `${(raw as number).toFixed(0)}%`;
  return formatNumber(raw, 0);
}
