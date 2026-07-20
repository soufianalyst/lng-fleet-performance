import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, Grid, Skeleton, IconButton, Chip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart,
} from 'recharts';
import { useApi, usePolling } from '../hooks/useApi';
import { getVessel, getVesselTelemetry, getVesselCII, getECAEvents, getCharterParties } from '../services/api';
import { ciiColor, formatDate } from '../utils/formatters';
import type { TelemetryPoint } from '../services/types';

function Gauge({ value, max, label, unit, color }: {
  value: number; max: number; label: string; unit: string; color: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <Box sx={{ textAlign: 'center', py: 1 }}>
      <Box sx={{ position: 'relative', display: 'inline-block' }}>
        <svg width="90" height="60" viewBox="0 0 90 60">
          <path d="M 10 55 A 35 35 0 1 1 80 55" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
          <path d="M 10 55 A 35 35 0 1 1 80 55" fill="none" stroke={color} strokeWidth="6" strokeDasharray={`${pct * 0.88} 100`} strokeLinecap="round" />
        </svg>
        <Typography variant="h6" sx={{ position: 'absolute', top: '18px', left: '50%', transform: 'translateX(-50%)', fontFamily: "'JetBrains Mono', monospace", fontSize: '1rem' }}>
          {value.toFixed(1)}
        </Typography>
      </Box>
      <Typography variant="caption" sx={{ color: '#8896b0', display: 'block', mt: 0.5 }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ color: '#555', fontSize: '0.6rem' }}>
        {unit}
      </Typography>
    </Box>
  );
}

export default function VesselDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const vesselRes = useApi(() => getVessel(id!), [id]);
  const telemetryRes = usePolling(() => getVesselTelemetry(id!, { from: new Date(Date.now() - 86400000).toISOString() }), 30000, [id]);
  const ciiRes = useApi(() => getVesselCII(id!), [id]);
  const ecaRes = useApi(() => getECAEvents(id!), [id]);
  const charterRes = useApi(() => getCharterParties(id!), [id]);

  const vessel = vesselRes.data;
  const telemetry = telemetryRes.data || [];
  const ciiRecords = ciiRes.data || [];
  const ecaEvents = ecaRes.data || [];
  const charters = charterRes.data || [];

  const latestTelemetry: TelemetryPoint | undefined = telemetry[telemetry.length - 1];

  if (vesselRes.loading) {
    return (
      <Box sx={{ p: 3, height: '100vh', bgcolor: '#0a0e17' }}>
        <Skeleton variant="rectangular" height={40} width={200} sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Grid item xs={12} md={6} key={i}>
              <Skeleton variant="rectangular" height={200} sx={{ bgcolor: '#111827' }} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (vesselRes.error) {
    return (
      <Box sx={{ p: 3, height: '100vh', bgcolor: '#0a0e17', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <Typography color="error" variant="h6">Failed to load vessel</Typography>
        <Typography color="text.secondary">{vesselRes.error}</Typography>
      </Box>
    );
  }

  if (!vessel) {
    return (
      <Box sx={{ p: 3, height: '100vh', bgcolor: '#0a0e17', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="text.secondary">Vessel not found</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100vh', overflow: 'auto', bgcolor: '#0a0e17', p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={() => navigate('/')} sx={{ color: '#40c4ff' }}>
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h5" sx={{ color: '#e0e6f0' }}>
            {vessel.name}
          </Typography>
          <Typography variant="caption" sx={{ color: '#8896b0' }}>
            IMO {vessel.imo} • {vessel.flag} • Built {vessel.built}
          </Typography>
        </Box>
        <Chip
          label={vessel.status.replace('-', ' ').toUpperCase()}
          size="small"
          sx={{
            ml: 'auto',
            bgcolor: vessel.status === 'at-sea' ? 'rgba(0,230,118,0.15)' : 'rgba(255,215,64,0.15)',
            color: vessel.status === 'at-sea' ? '#00e676' : '#ffd740',
            fontWeight: 600,
          }}
        />
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Vessel Info
              </Typography>
              <Box sx={{ mt: 1, '& > div': { display: 'flex', justifyContent: 'space-between', py: 0.5, borderBottom: '1px solid rgba(64,196,255,0.06)' } }}>
                <Box><Typography variant="body2">Flag</Typography><Typography variant="body2" sx={{ color: '#e0e6f0' }}>{vessel.flag}</Typography></Box>
                <Box><Typography variant="body2">Built</Typography><Typography variant="body2" sx={{ color: '#e0e6f0' }}>{vessel.built}</Typography></Box>
                <Box><Typography variant="body2">Capacity</Typography><Typography variant="body2" sx={{ color: '#e0e6f0' }}>{vessel.capacity.toLocaleString()} m³</Typography></Box>
                <Box><Typography variant="body2">Engine</Typography><Typography variant="body2" sx={{ color: '#e0e6f0' }}>{vessel.engineType}</Typography></Box>
                <Box><Typography variant="body2">BOR</Typography><Typography variant="body2" sx={{ color: '#e0e6f0' }}>{vessel.boilOffRate}%/day</Typography></Box>
                <Box><Typography variant="body2">CII Rating</Typography>
                  <Typography variant="body2" sx={{ color: ciiColor(vessel.ciiRating), fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>
                    {vessel.ciiRating}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Telemetry Gauges
              </Typography>
              {latestTelemetry ? (
                <Grid container spacing={0}>
                  <Grid item xs={3}><Gauge value={latestTelemetry.speed} max={22} label="Speed" unit="knots" color="#40c4ff" /></Grid>
                  <Grid item xs={3}><Gauge value={latestTelemetry.shaftPower / 1000} max={50} label="Power" unit="MW" color="#00e676" /></Grid>
                  <Grid item xs={3}><Gauge value={latestTelemetry.boilOffRate} max={0.3} label="BOR" unit="%/day" color="#ffd740" /></Grid>
                  <Grid item xs={3}><Gauge value={latestTelemetry.engineLoad} max={100} label="Eng Load" unit="%" color="#ff6e40" /></Grid>
                </Grid>
              ) : (
                <Typography variant="body2" sx={{ color: '#555', py: 2, textAlign: 'center' }}>
                  No telemetry data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                24h Trend
              </Typography>
              {telemetry.length > 1 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={telemetry}>
                    <defs>
                      <linearGradient id="colSpeed" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#40c4ff" stopOpacity={0.3} /><stop offset="100%" stopColor="#40c4ff" stopOpacity={0} /></linearGradient>
                      <linearGradient id="colPower" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#00e676" stopOpacity={0.3} /><stop offset="100%" stopColor="#00e676" stopOpacity={0} /></linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(64,196,255,0.06)" />
                    <XAxis dataKey="timestamp" tickFormatter={(v: string) => new Date(v).toLocaleTimeString()} stroke="#555" fontSize={10} />
                    <YAxis stroke="#555" fontSize={10} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid rgba(64,196,255,0.2)', borderRadius: 8 }}
                      labelStyle={{ color: '#e0e6f0' }}
                    />
                    <Area type="monotone" dataKey="speed" stroke="#40c4ff" fill="url(#colSpeed)" name="Speed (kn)" dot={false} strokeWidth={2} />
                    <Area type="monotone" dataKey="shaftPower" stroke="#00e676" fill="url(#colPower)" name="Shaft Power (kW)" dot={false} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" sx={{ color: '#555', py: 3, textAlign: 'center' }}>
                  Waiting for telemetry data...
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                CII Performance
              </Typography>
              {ciiRecords.length > 0 ? (
                <Box sx={{ mt: 1 }}>
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={ciiRecords}>
                      <CartesianGrid stroke="rgba(64,196,255,0.06)" />
                      <XAxis dataKey="year" stroke="#555" fontSize={10} />
                      <YAxis stroke="#555" fontSize={10} />
                      <Tooltip
                        contentStyle={{ background: '#111827', border: '1px solid rgba(64,196,255,0.2)', borderRadius: 8 }}
                      />
                      <Line type="monotone" dataKey="attainedCII" stroke="#40c4ff" name="Attained" dot strokeWidth={2} />
                      <Line type="monotone" dataKey="requiredCII" stroke="#ff6e40" name="Required" dot strokeWidth={2} strokeDasharray="4 4" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Typography variant="body2" sx={{ color: '#555', py: 2, textAlign: 'center' }}>No CII data</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                ECA Compliance Timeline
              </Typography>
              {ecaEvents.length > 0 ? (
                <Box sx={{ mt: 1 }}>
                  {ecaEvents.slice(0, 5).map((e) => (
                    <Box key={e.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5, borderBottom: '1px solid rgba(64,196,255,0.06)' }}>
                      <Chip label={e.zone} size="small" sx={{ bgcolor: 'rgba(0,200,255,0.1)', color: '#40c4ff', fontSize: '0.65rem' }} />
                      <Typography variant="caption">{formatDate(e.entryTime)}</Typography>
                      <Chip
                        label={e.complianceStatus.replace('-', ' ')}
                        size="small"
                        sx={{
                          ml: 'auto',
                          bgcolor: e.complianceStatus === 'compliant' ? 'rgba(0,230,118,0.1)' : 'rgba(255,23,68,0.1)',
                          color: e.complianceStatus === 'compliant' ? '#00e676' : '#ff1744',
                          fontSize: '0.65rem',
                        }}
                      />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" sx={{ color: '#555', py: 2, textAlign: 'center' }}>No ECA events</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Charter Party Status
              </Typography>
              {charters.length > 0 ? (
                <Box sx={{ mt: 1 }}>
                  {charters.map((c) => (
                    <Box key={c.id} sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1, borderBottom: '1px solid rgba(64,196,255,0.06)' }}>
                      <Typography variant="body2" sx={{ color: '#e0e6f0' }}>{c.charterer}</Typography>
                      <Chip label={c.type} size="small" sx={{ bgcolor: 'rgba(64,196,255,0.1)', color: '#40c4ff', fontSize: '0.65rem' }} />
                      <Typography variant="caption">{formatDate(c.startDate)} - {formatDate(c.endDate)}</Typography>
                      <Chip
                        label={c.status}
                        size="small"
                        sx={{ ml: 'auto', bgcolor: c.status === 'active' ? 'rgba(0,230,118,0.1)' : 'rgba(144,164,174,0.1)', color: c.status === 'active' ? '#00e676' : '#8896b0', fontSize: '0.65rem' }}
                      />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" sx={{ color: '#555', py: 2, textAlign: 'center' }}>No charter party data</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
