import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, IconButton, Tooltip } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import GavelIcon from '@mui/icons-material/Gavel';
import FlightIcon from '@mui/icons-material/Flight';
import NotificationsIcon from '@mui/icons-material/Notifications';
import { useNavigate, useLocation } from 'react-router-dom';
import FleetOverview from './pages/FleetOverview';
import VesselDetail from './pages/VesselDetail';
import CIICompliance from './pages/CIICompliance';
import VoyageList from './pages/VoyageList';
import AlertCenter from './pages/AlertCenter';

const navItems = [
  { path: '/', label: 'Fleet', icon: <DashboardIcon /> },
  { path: '/cii', label: 'CII', icon: <GavelIcon /> },
  { path: '/voyages', label: 'Voyages', icon: <FlightIcon /> },
  { path: '/alerts', label: 'Alerts', icon: <NotificationsIcon /> },
];

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: '#0a0e17' }}>
      <AppBar
        position="fixed"
        sx={{
          width: 56,
          bgcolor: '#070b12',
          borderRight: '1px solid rgba(64,196,255,0.1)',
          boxShadow: 'none',
        }}
      >
        <Toolbar sx={{ flexDirection: 'column', gap: 1, px: 0, pt: 1 }}>
          <Typography
            variant="caption"
            sx={{
              color: '#40c4ff',
              fontWeight: 700,
              fontSize: '0.55rem',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              mb: 1,
            }}
          >
            LNG
          </Typography>
          {navItems.map((item) => (
            <Tooltip title={item.label} placement="right" key={item.path}>
              <IconButton
                onClick={() => navigate(item.path)}
                sx={{
                  color: location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
                    ? '#40c4ff'
                    : '#556',
                  bgcolor: location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
                    ? 'rgba(64,196,255,0.1)'
                    : 'transparent',
                  borderRadius: 2,
                  width: 40,
                  height: 40,
                  '&:hover': { bgcolor: 'rgba(64,196,255,0.15)', color: '#40c4ff' },
                }}
              >
                {item.icon}
              </IconButton>
            </Tooltip>
          ))}
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1, ml: '56px', overflow: 'hidden' }}>
        <Routes>
          <Route path="/" element={<FleetOverview />} />
          <Route path="/vessels/:id" element={<VesselDetail />} />
          <Route path="/cii" element={<CIICompliance />} />
          <Route path="/voyages" element={<VoyageList />} />
          <Route path="/alerts" element={<AlertCenter />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Box>
    </Box>
  );
}
