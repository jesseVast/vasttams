import React from 'react';
import { Container, Typography, Paper, Box } from '@mui/material';
import { authService } from '../services/api';

const Dashboard: React.FC = () => {
  const user = authService.getCurrentUser();

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mt: 2 }}>
        <Box sx={{ flex: '1 1 48%' }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Welcome
            </Typography>
            <Typography variant="body1">
              Logged in as: {user?.username} ({user?.role})
            </Typography>
          </Paper>
        </Box>
        <Box sx={{ flex: '1 1 48%' }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Access
            </Typography>
            <Typography variant="body2">
              • Manage Users
              • View Sources
              • Manage Flows
              • Browse Segments
            </Typography>
          </Paper>
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;

