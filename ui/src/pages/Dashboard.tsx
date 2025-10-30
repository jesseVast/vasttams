import React, { useEffect, useState } from 'react';
import { Container, Typography, Paper, Box, CircularProgress } from '@mui/material';
import { authService, analyticsService } from '../services/api';
import { AnalyticsSummary } from '../types';

const Dashboard: React.FC = () => {
  const user = authService.getCurrentUser();
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStatistics = async () => {
      try {
        setLoading(true);
        const summary = await analyticsService.getSummary().catch(() => null);
        setAnalytics(summary);
      } catch (error) {
        console.error('Failed to load statistics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStatistics();
  }, []);

  const formatStorageSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

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

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading statistics...</Typography>
        </Box>
      ) : analytics ? (
        <>
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Overview Statistics
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 2 }}>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h2" color="primary">
                  {analytics.counts.total_sources}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  Sources
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h2" color="primary">
                  {analytics.counts.total_flows}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  Flows
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h2" color="primary">
                  {analytics.counts.total_segments}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  Segments
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h2" color="primary">
                  {analytics.counts.total_objects}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  Objects
                </Typography>
              </Paper>
            </Box>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Storage Statistics
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 2 }}>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h4" color="primary">
                  {formatStorageSize(analytics.storage.total_size_bytes)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Storage
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  ({analytics.storage.total_size_gb.toFixed(2)} GB)
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h4" color="primary">
                  {formatStorageSize(analytics.storage.average_size_bytes)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Object Size
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.storage.object_count_with_size}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Objects with Size
                </Typography>
              </Paper>
              {analytics.storage.min_size_bytes !== null && (
                <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                  <Typography variant="h4" color="primary">
                    {formatStorageSize(analytics.storage.min_size_bytes)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Min Object Size
                  </Typography>
                </Paper>
              )}
              {analytics.storage.max_size_bytes !== null && (
                <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px', minWidth: '180px' }}>
                  <Typography variant="h4" color="primary">
                    {formatStorageSize(analytics.storage.max_size_bytes)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Max Object Size
                  </Typography>
                </Paper>
              )}
            </Box>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Format Breakdown
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 2 }}>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 150px', minWidth: '150px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.formats.video_flows}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Video Flows
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 150px', minWidth: '150px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.formats.audio_flows}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Audio Flows
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 150px', minWidth: '150px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.formats.image_flows}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Image Flows
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 150px', minWidth: '150px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.formats.data_flows}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Data Flows
                </Typography>
              </Paper>
              <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 150px', minWidth: '150px' }}>
                <Typography variant="h4" color="primary">
                  {analytics.formats.multi_flows}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Multi Flows
                </Typography>
              </Paper>
            </Box>
          </Box>

        </>
      ) : (
        <Box sx={{ mt: 3 }}>
          <Typography color="error">
            Failed to load analytics data. Please refresh the page.
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default Dashboard;

