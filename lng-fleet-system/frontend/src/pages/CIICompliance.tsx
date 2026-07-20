import React from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Skeleton, Tabs, Tab,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { useApi } from '../hooks/useApi';
import { getFleetCII, getEtsStatus, getFuelEUBalance } from '../services/api';
import { formatCII, ciiColor, ciiBgColor, formatCurrency, formatEmissions } from '../utils/formatters';

export default function CIICompliance() {
  const [tab, setTab] = React.useState(0);
  const ciiRes = useApi(() => getFleetCII(new Date().getFullYear()), []);
  const etsRes = useApi(() => getEtsStatus(), []);
  const fuelEURes = useApi(() => getFuelEUBalance(), []);

  const ciiData = ciiRes.data || [];
  const etsData = etsRes.data || [];
  const fuelEUData = fuelEURes.data || [];

  return (
    <Box sx={{ height: '100vh', overflow: 'auto', bgcolor: '#0a0e17', p: 2 }}>
      <Typography variant="h5" sx={{ color: '#e0e6f0', mb: 2 }}>
        CII & Compliance Dashboard
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{
          mb: 2,
          '& .MuiTab-root': { color: '#8896b0', textTransform: 'none', fontWeight: 500 },
          '& .Mui-selected': { color: '#40c4ff' },
        }}
      >
        <Tab label="CII Fleet Overview" />
        <Tab label="EU ETS Tracker" />
        <Tab label="FuelEU Compliance" />
      </Tabs>

      {tab === 0 && (
        <>
          {ciiRes.loading ? (
            <Skeleton variant="rectangular" height={300} sx={{ bgcolor: '#111827', borderRadius: 2 }} />
          ) : ciiRes.error ? (
            <Typography color="error">{ciiRes.error}</Typography>
          ) : ciiData.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>No CII data available for this year</Typography>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                      Fleet CII Ratings
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Vessel</TableCell>
                            <TableCell align="right">Attained CII</TableCell>
                            <TableCell align="right">Required CII</TableCell>
                            <TableCell align="center">Rating</TableCell>
                            <TableCell align="center">Trend</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {ciiData.map((r) => (
                            <TableRow key={`${r.vesselId}-${r.year}`}>
                              <TableCell>{r.vesselName}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{formatCII(r.attainedCII)}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{formatCII(r.requiredCII)}</TableCell>
                              <TableCell align="center">
                                <Chip
                                  label={r.rating}
                                  size="small"
                                  sx={{ bgcolor: ciiBgColor(r.rating), color: ciiColor(r.rating), fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}
                                />
                              </TableCell>
                              <TableCell align="center">
                                <Chip
                                  label={r.trend}
                                  size="small"
                                  sx={{
                                    bgcolor: r.trend === 'improving' ? 'rgba(0,230,118,0.1)' : r.trend === 'declining' ? 'rgba(255,23,68,0.1)' : 'rgba(255,215,64,0.1)',
                                    color: r.trend === 'improving' ? '#00e676' : r.trend === 'declining' ? '#ff1744' : '#ffd740',
                                  }}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                      CII Rating Distribution
                    </Typography>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={['A','B','C','D','E'].map((r) => ({ rating: r, count: ciiData.filter((c) => c.rating === r).length }))}>
                        <CartesianGrid stroke="rgba(64,196,255,0.06)" />
                        <XAxis dataKey="rating" stroke="#555" />
                        <YAxis stroke="#555" />
                        <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(64,196,255,0.2)', borderRadius: 8 }} />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {['A','B','C','D','E'].map((r) => (
                            <Cell key={r} fill={ciiColor(r)} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </>
      )}

      {tab === 1 && (
        <Grid container spacing={2}>
          {etsRes.loading ? (
            <Grid item xs={12}><Skeleton variant="rectangular" height={300} sx={{ bgcolor: '#111827', borderRadius: 2 }} /></Grid>
          ) : etsRes.error ? (
            <Typography color="error">{etsRes.error}</Typography>
          ) : etsData.length === 0 ? (
            <Grid item xs={12}><Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>No EU ETS data available</Typography></Grid>
          ) : (
            <>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                      EU ETS Allowance Tracker
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Vessel</TableCell>
                            <TableCell align="right">Total Emissions</TableCell>
                            <TableCell align="right">Allowances</TableCell>
                            <TableCell align="right">Surplus/Deficit</TableCell>
                            <TableCell align="right">Est. Liability</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {etsData.map((e) => (
                            <TableRow key={`${e.vesselId}-${e.year}`}>
                              <TableCell>{e.vesselName}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{formatEmissions(e.totalEmissions)}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{e.allowanceAllocated.toLocaleString()}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace", color: e.surplusDeficit >= 0 ? '#00e676' : '#ff1744' }}>
                                {e.surplusDeficit >= 0 ? '+' : ''}{e.surplusDeficit.toLocaleString()}
                              </TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace", color: '#ff6e40' }}>{formatCurrency(e.estimatedLiability)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Total EUA Liability
                    </Typography>
                    <Typography variant="h4" sx={{ color: '#ff6e40', fontFamily: "'JetBrains Mono', monospace", mt: 1 }}>
                      {formatCurrency(etsData.reduce((s, e) => s + e.estimatedLiability, 0))}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      Total Allowance Surplus
                    </Typography>
                    <Typography variant="h4" sx={{ color: '#00e676', fontFamily: "'JetBrains Mono', monospace", mt: 1 }}>
                      {etsData.reduce((s, e) => s + e.surplusDeficit, 0).toLocaleString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </>
          )}
        </Grid>
      )}

      {tab === 2 && (
        <Grid container spacing={2}>
          {fuelEURes.loading ? (
            <Grid item xs={12}><Skeleton variant="rectangular" height={300} sx={{ bgcolor: '#111827', borderRadius: 2 }} /></Grid>
          ) : fuelEURes.error ? (
            <Typography color="error">{fuelEURes.error}</Typography>
          ) : fuelEUData.length === 0 ? (
            <Grid item xs={12}><Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>No FuelEU data available</Typography></Grid>
          ) : (
            <>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                      FuelEU Intensity Balance
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Vessel</TableCell>
                            <TableCell align="right">CO₂ Intensity</TableCell>
                            <TableCell align="right">Reference</TableCell>
                            <TableCell align="right">Surplus</TableCell>
                            <TableCell align="right">Penalty</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {fuelEUData.map((f) => (
                            <TableRow key={`${f.vesselId}-${f.year}`}>
                              <TableCell>{f.vesselName}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{f.co2Intensity.toFixed(2)}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>{f.referenceIntensity.toFixed(2)}</TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace", color: f.surplus >= 0 ? '#00e676' : '#ff1744' }}>
                                {f.surplus.toFixed(2)}
                              </TableCell>
                              <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono', monospace", color: '#ff6e40' }}>
                                {f.penalty > 0 ? formatCurrency(f.penalty) : '—'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="caption" sx={{ color: '#8896b0', textTransform: 'uppercase', letterSpacing: '0.06em', mb: 1, display: 'block' }}>
                      Compliance Balance by Vessel
                    </Typography>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={fuelEUData}>
                        <CartesianGrid stroke="rgba(64,196,255,0.06)" />
                        <XAxis dataKey="vesselName" stroke="#555" fontSize={10} />
                        <YAxis stroke="#555" />
                        <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(64,196,255,0.2)', borderRadius: 8 }} />
                        <Bar dataKey="complianceBalance" radius={[4, 4, 0, 0]}>
                          {fuelEUData.map((_, i) => (
                            <Cell key={i} fill={fuelEUData[i].complianceBalance >= 0 ? '#00e676' : '#ff1744'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </Grid>
            </>
          )}
        </Grid>
      )}
    </Box>
  );
}
