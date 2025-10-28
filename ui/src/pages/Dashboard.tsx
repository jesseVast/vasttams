import React, { useEffect, useState } from 'react';
import { Container, Typography, Paper, Box, CircularProgress } from '@mui/material';
import { authService, sourceService, flowService, userService } from '../services/api';

interface Statistics {
  users: number;
  sources: number;
  flows: number;
  loading: boolean;
}

const Dashboard: React.FC = () => {
  const user = authService.getCurrentUser();
  const [stats, setStats] = useState<Statistics>({
    users: 0,
    sources: 0,
    flows: 0,
    loading: true,
  });

  useEffect(() => {
    const loadStatistics = async () => {
      try {
        const [sources, flows, users] = await Promise.all([
          sourceService.list().catch(() => []),
          flowService.list().catch(() => []),
          userService.list().catch(() => []),
        ]);

        setStats({
          users: users.length,
          sources: sources.length,
          flows: flows.length,
          loading: false,
        });
      } catch (error) {
        console.error('Failed to load statistics:', error);
        setStats({ users: 0, sources: 0, flows: 0, loading: false });
      }
    };

    loadStatistics();
  }, []);

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Welcome, {user?.username} ({user?.role})
        </Typography>
      </Box>

      {stats.loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading statistics...</Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 2 }}>
          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 250px', minWidth: '200px' }}>
            <Typography variant="h2" color="primary">
              {stats.sources}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              Sources
            </Typography>
          </Paper>
          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 250px', minWidth: '200px' }}>
            <Typography variant="h2" color="primary">
              {stats.flows}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              Flows
            </Typography>
          </Paper>
          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 250px', minWidth: '200px' }}>
            <Typography variant="h2" color="primary">
              {stats.users}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              Users
            </Typography>
          </Paper>
        </Box>
      )}

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 2 }}>
          <Paper sx={{ p: 2, flex: '1 1 200px' }}>
            <Typography variant="body1" fontWeight="bold">
              Sources
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage media sources and configurations
            </Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: '1 1 200px' }}>
            <Typography variant="body1" fontWeight="bold">
              Flows
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View and manage media flows
            </Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: '1 1 200px' }}>
            <Typography variant="body1" fontWeight="bold">
              Users
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage user accounts and permissions
            </Typography>
          </Paper>
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;

