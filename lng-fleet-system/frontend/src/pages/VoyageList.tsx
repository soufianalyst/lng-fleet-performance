import { useState, useMemo } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, TextField, MenuItem, Skeleton,
  InputAdornment,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getVoyages } from '../services/api';
import { formatDate, formatNumber, statusLabel } from '../utils/formatters';

export default function VoyageList() {
  const navigate = useNavigate();
  const voyagesRes = useApi(() => getVoyages(), []);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = useMemo(() => {
    const voyages = voyagesRes.data || [];
    return voyages.filter((v) => {
      if (statusFilter !== 'all' && v.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          v.vesselName.toLowerCase().includes(q) ||
          v.departurePort.toLowerCase().includes(q) ||
          v.arrivalPort.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [voyagesRes.data, search, statusFilter]);

  return (
    <Box sx={{ height: '100vh', overflow: 'auto', bgcolor: '#0a0e17', p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ color: '#e0e6f0' }}>
          Voyages
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            size="small"
            placeholder="Search vessels, ports..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#555', fontSize: 18 }} /></InputAdornment>,
              sx: { color: '#e0e6f0', bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1, fontSize: '0.85rem', '& fieldset': { borderColor: 'rgba(64,196,255,0.15)' } },
            }}
            sx={{ minWidth: 220 }}
          />
          <TextField
            select
            size="small"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            InputProps={{ sx: { color: '#e0e6f0', bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1, fontSize: '0.85rem', '& fieldset': { borderColor: 'rgba(64,196,255,0.15)' } } }}
            sx={{ minWidth: 130 }}
          >
            <MenuItem value="all">All Status</MenuItem>
            <MenuItem value="planned">Planned</MenuItem>
            <MenuItem value="in-progress">In Progress</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="cancelled">Cancelled</MenuItem>
          </TextField>
        </Box>
      </Box>

      {voyagesRes.loading ? (
        <Skeleton variant="rectangular" height={400} sx={{ bgcolor: '#111827', borderRadius: 2 }} />
      ) : voyagesRes.error ? (
        <Typography color="error">{voyagesRes.error}</Typography>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary">
              {voyagesRes.data?.length === 0 ? 'No voyages recorded yet' : 'No voyages match your filters'}
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
                    <TableCell>Vessel</TableCell>
                    <TableCell>Route</TableCell>
                    <TableCell>Departure</TableCell>
                    <TableCell>Arrival</TableCell>
                    <TableCell align="right">Distance (nm)</TableCell>
                    <TableCell align="right">Cargo (m³)</TableCell>
                    <TableCell align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filtered.map((v) => (
                    <TableRow
                      key={v.id}
                      hover
                      onClick={() => navigate(`/vessels/${v.vesselId}`)}
                      sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'rgba(64,196,255,0.04)' } }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ color: '#e0e6f0', fontWeight: 500 }}>
                          {v.vesselName}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {v.departurePort} → {v.arrivalPort}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">{formatDate(v.departureTime)}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">{formatDate(v.arrivalTime)}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                          {formatNumber(v.distance, 0)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                          {formatNumber(v.cargoQuantity, 0)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={statusLabel(v.status)}
                          size="small"
                          sx={{
                            bgcolor: v.status === 'in-progress' ? 'rgba(0,230,118,0.1)' : v.status === 'completed' ? 'rgba(64,196,255,0.1)' : 'rgba(144,164,174,0.1)',
                            color: v.status === 'in-progress' ? '#00e676' : v.status === 'completed' ? '#40c4ff' : '#8896b0',
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
      )}
    </Box>
  );
}
