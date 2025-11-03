import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Sources from './pages/Sources';
import Flows from './pages/Flows';
import Segments from './pages/Segments';
import StorageBackends from './pages/StorageBackends';
import { authService } from './services/api';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const user = authService.getCurrentUser();
  return user ? <>{children}</> : <Navigate to="/login" />;
};

interface AdminRouteProps {
  children: React.ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const user = authService.getCurrentUser();
  if (!user) {
    return <Navigate to="/login" />;
  }
  if (user.role !== 'admin') {
    return <Navigate to="/" />;
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route
              index
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="sources"
              element={
                <PrivateRoute>
                  <Sources />
                </PrivateRoute>
              }
            />
            <Route
              path="flows"
              element={
                <PrivateRoute>
                  <Flows />
                </PrivateRoute>
              }
            />
            <Route
              path="segments"
              element={
                <PrivateRoute>
                  <Segments />
                </PrivateRoute>
              }
            />
            <Route
              path="users"
              element={
                <AdminRoute>
                  <Users />
                </AdminRoute>
              }
            />
            <Route
              path="storage-backends"
              element={
                <AdminRoute>
                  <StorageBackends />
                </AdminRoute>
              }
            />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
};

export default App;
