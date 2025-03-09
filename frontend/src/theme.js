// src/theme.js
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#18181b', // Global background color (Tailwind zinc-900)
      paper: '#27272a',   // Paper background (Tailwind zinc-800)
    },
    primary: {
      main: '#4A90E2',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#F5A623',
      contrastText: '#FFFFFF',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#d4d4d8', // Updated secondary text color (Tailwind zinc-300)
    },
    // Custom colors for components (chip buttons, borders, etc.)
    custom: {
      // For chip buttons:
      greenMain: '#90C43E',
      greenHoverBg: 'rgba(144,196,62,0.1)',
      
      indigoMain: '#4F39F6',
      indigoHoverBg: 'rgba(79,57,246,0.1)',
      
      greyBorder: '#707070',
      greyHoverBg: 'rgba(112,112,112,0.1)',
      greyText: '#a0a0a0',

      // Common border colors:
      borderDefault: '#3f3f46', // Tailwind zinc-700
      borderHover: '#5f5f66',   // Approximate Tailwind zinc-600

      // For the "Add" button:
      successBorder: '#00a63e',
      successBg: '#0d542b',
      successBgHover: '#0a4020',
      successIcon: '#05DF72',
    },
  },
  typography: {
    // Set Inter as the global font
    fontFamily: 'Inter, sans-serif',
    h1: { fontSize: '2.5rem', fontWeight: 700 },
    h2: { fontSize: '2rem', fontWeight: 700 },
    body1: { fontSize: '1rem' },
  },
  spacing: 8,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#27272a', // Use the same paper color
          color: '#FFFFFF',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#18181b',
        },
      },
    },
  },
  custom: {
    sidebar: {
      activeBackground: 'rgba(21, 69, 62, 0.67)',
      activeBorder: '#14917e',
      hoverBackground: '#27272a',
      hoverBorder: '#3f3f46',
      fontFamily: 'Inter, sans-serif',
    },
  },
});

export default theme;
