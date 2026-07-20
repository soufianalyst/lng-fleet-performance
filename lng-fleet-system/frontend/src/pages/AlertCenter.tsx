import { useState, useMemo, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Button, Skeleton, IconButton,
  Tabs, Tab,
} from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { useApi } from '../hooks/useApi';
import { getAlerts, acknowledgeAlert } from '../services/api';
import { formatDateTime, formatTimeAgo, severityColor } from '../utils/formatters';

export default function AlertCenter() {
  const [severityFilter, setSeverityFilter] = useState('all');
  const alertsRes = useApi(() => getAlerts(), []);

  const handleAcknowledge = useCallback(async (id: string) => {
    try {
      await acknowledgeAlert(id, 'operator');
      alertsRes.refresh();
    } catch {
      // silently fail
    }
  }, [alertsRes.refresh]);

  const filtered = useMemo(() => {
    const alerts = alertsRes.data || [];
    return severityFilter === 'all'
      ? alerts
      : alerts.filter((a) => a.severity === severityFilter);
  }, [alertsRes.data, severityFilter]);

  const unacknowledgedCount = useMemo(
    () => (alertsRes.data || []).filter((a) => !a.acknowledged).length,
    [alertsRes.data]
  );

  return (
    <Box sx={{ height: '100vh', overflow: 'auto', bgcolor: '#0a0e17', p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h5" sx={{ color: '#e0e6f0' }}>
            Alert Center
          </Typography>
          <Typography variant="caption" sx={{ color: unacknowledgedCount > 0 ? '#ff6e40' : '#00e676' }}>
            {unacknowledgedCount} unacknowledged alert{unacknowledgedCount !== 1 ? 's' : ''}
          </Typography>
        </Box>
        <Button size="small" variant="outlined" sx={{ borderColor: 'rgba(64,196,255,0.3)' }} onClick={() => alertsRes.refresh()}>
          Refresh
        </Button>
      </Box>

      <Tabs
        value={severityFilter}
        onChange={(_, v) => setSeverityFilter(v)}
        sx={{
          mb: 2,
          '& .MuiTab-root': { color: '#8896b0', textTransform: 'none', fontWeight: 500, minHeight: 36 },
          '& .Mui-selected': { color: '#40c4ff' },
        }}
      >
        <Tab label="All" value="all" />
        <Tab label="Critical" value="critical" />
        <Tab label="High" value="high" />
        <Tab label="Medium" value="medium" />
        <Tab label="Low" value="low" />
      </Tabs>

      {alertsRes.loading ? (
        <Skeleton variant="rectangular" height={400} sx={{ bgcolor: '#111827', borderRadius: 2 }} />
      ) : alertsRes.error ? (
        <Typography color="error">{alertsRes.error}</Typography>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent sx={{ py: 6, textAlign: 'center' }}>
            <ErrorOutlineIcon sx={{ fontSize: 48, color: '#333', mb: 1 }} />
            <Typography color="text.secondary">
              {alertsRes.data?.length === 0 ? 'No alerts in the system' : 'No alerts match this severity level'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Severity</TableCell>
                    <TableCell>Vessel</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Time</TableCell>
                    <TableCell align="center">Status</TableCell>
                    <TableCell align="center">Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filtered.map((alert) => (
                    <TableRow
                      key={alert.id}
                      sx={{
                        '&:hover': { bgcolor: 'rgba(64,196,255,0.04)' },
                        ...(alert.severity === 'critical' && !alert.acknowledged
                          ? { bgcolor: 'rgba(255,23,68,0.04)' }
                          : {}),
                      }}
                    >
                      <TableCell>
                        <Chip
                          label={alert.severity.toUpperCase()}
                          size="small"
                          sx={{
                            bgcolor: `${severityColor(alert.severity)}22`,
                            color: severityColor(alert.severity),
                            fontWeight: 600,
                            fontSize: '0.65rem',
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: '#e0e6f0', fontWeight: 500 }}>
                          {alert.vesselName}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={alert.type}
                          size="small"
                          sx={{ bgcolor: 'rgba(64,196,255,0.08)', color: '#40c4ff', fontSize: '0.65rem', textTransform: 'capitalize' }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ color: '#c8d0e0' }}>
                          {alert.title}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#667' }}>
                          {alert.message}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ whiteSpace: 'nowrap' }}>
                          {formatTimeAgo(alert.timestamp)}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#555', display: 'block', fontSize: '0.6rem' }}>
                          {formatDateTime(alert.timestamp)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={alert.acknowledged ? 'Acknowledged' : 'Open'}
                          size="small"
                          sx={{
                            bgcolor: alert.acknowledged ? 'rgba(0,230,118,0.1)' : 'rgba(255,110,64,0.1)',
                            color: alert.acknowledged ? '#00e676' : '#ff6e40',
                            fontSize: '0.65rem',
                          }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        {!alert.acknowledged ? (
                          <IconButton
                            size="small"
                            onClick={() => handleAcknowledge(alert.id)}
                            sx={{ color: '#00e676' }}
                            title="Acknowledge"
                          >
                            <CheckCircleOutlineIcon fontSize="small" />
                          </IconButton>
                        ) : (
                          <Typography variant="caption" sx={{ color: '#555' }}>
                            {alert.acknowledgedBy || 'System'}
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
