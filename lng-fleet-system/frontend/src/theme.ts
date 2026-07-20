import { createTheme } from '@mui/material/styles';

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#40c4ff', light: '#80d8ff', dark: '#0091ea' },
    secondary: { main: '#00e676', light: '#69f0ae', dark: '#00c853' },
    error: { main: '#ff1744' },
    warning: { main: '#ffd740' },
    info: { main: '#40c4ff' },
    background: {
      default: '#0a0e17',
      paper: '#111827',
    },
    text: {
      primary: '#e0e6f0',
      secondary: '#8896b0',
    },
    divider: 'rgba(64, 196, 255, 0.12)',
  },
  typography: {
    fontFamily: "'Inter', sans-serif",
    h4: { fontWeight: 600, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    body2: { color: '#8896b0' },
    caption: { fontFamily: "'JetBrains Mono', monospace", fontSize: '0.75rem' },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(135deg, #111827 0%, #0f1729 100%)',
          border: '1px solid rgba(64, 196, 255, 0.1)',
          backdropFilter: 'blur(12px)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(64, 196, 255, 0.08)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
  },
});
