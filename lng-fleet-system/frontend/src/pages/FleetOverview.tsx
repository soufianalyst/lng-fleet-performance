import { useCallback, useMemo } from 'react';
import {
  Box, Typography, Card, CardContent, Skeleton, Button, Chip,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import FleetMap from '../components/FleetMap';
import FleetSummaryCards from '../components/FleetSummaryCards';
import { usePolling } from '../hooks/useApi';
import { getVessels, getVoyages, getDashboardSummary } from '../services/api';
import { severityColor } from '../utils/formatters';

export default function FleetOverview() {
  const navigate = useNavigate();

  const vesselsRes = usePolling(getVessels, 30000);
  const voyagesRes = usePolling(() => getVoyages({ status: 'in-progress' }), 60000);
  const summaryRes = usePolling(getDashboardSummary, 30000);

  const handleVesselClick = useCallback(
    (id: string) => navigate(`/vessels/${id}`),
    [navigate]
  );

  const recentAlerts = useMemo(() => {
    if (!vesselsRes.data) return [];
    return vesselsRes.data.slice(0, 5).map((v) => ({
      id: v.id,
      vesselName: v.name,
      type: 'cii' as const,
      severity: (v.ciiRating === 'E' ? 'critical' : v.ciiRating === 'D' ? 'high' : 'low') as 'critical' | 'high' | 'low',
      title: `CII Rating: ${v.ciiRating}`,
      timestamp: new Date().toISOString(),
    }));
  }, [vesselsRes.data]);

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 2, gap: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 1 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#e0e6f0', letterSpacing: '0.02em' }}>
            Fleet Command
          </Typography>
          <Typography variant="caption" sx={{ color: '#40c4ff' }}>
            LNG Fleet • Real-time Monitoring
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" variant="outlined" sx={{ borderColor: 'rgba(64,196,255,0.3)' }} onClick={() => navigate('/alerts')}>
            Alert Center
          </Button>
          <Button size="small" variant="outlined" sx={{ borderColor: 'rgba(64,196,255,0.3)' }} onClick={() => navigate('/cii')}>
            CII Dashboard
          </Button>
        </Box>
      </Box>

      <FleetSummaryCards summary={summaryRes.data} loading={summaryRes.loading} />

      <Card sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <CardContent sx={{ flex: 1, p: 0, '&:last-child': { pb: 0 }, position: 'relative' }}>
          {vesselsRes.loading ? (
            <Skeleton variant="rectangular" sx={{ height: '100%', width: '100%', bgcolor: '#111827' }} />
          ) : vesselsRes.error ? (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Typography color="error">{vesselsRes.error}</Typography>
            </Box>
          ) : (
            <FleetMap
              vessels={vesselsRes.data || []}
              voyages={voyagesRes.data || undefined}
              onVesselClick={handleVesselClick}
            />
          )}
        </CardContent>
      </Card>

      <Card sx={{ flexShrink: 0 }}>
        <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Typography variant="caption" sx={{ color: '#8896b0', mb: 1, display: 'block' }}>
            Recent Fleet Alerts
          </Typography>
          {recentAlerts.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#555' }}>No active alerts</Typography>
          ) : (
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {recentAlerts.map((alert) => (
                <Chip
                  key={alert.id}
                  label={`${alert.vesselName}: ${alert.title}`}
                  size="small"
                  sx={{
                    bgcolor: `${severityColor(alert.severity)}22`,
                    color: severityColor(alert.severity),
                    borderColor: severityColor(alert.severity),
                    border: '1px solid',
                    fontSize: '0.7rem',
                  }}
                />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
