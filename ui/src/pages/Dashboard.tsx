import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, CircularProgress } from '@mui/material';
import { authService, analyticsService } from '../services/api';
import { AnalyticsSummary } from '../types';
import StatCard from '../components/StatCard';

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
            <Box sx={{ display: 'flex', gap: 3, mt: 2 }}>
              <StatCard
                value={analytics.counts.total_sources}
                label="Sources"
              />
              <StatCard
                value={analytics.counts.total_flows}
                label="Flows"
              />
              <StatCard
                value={analytics.counts.total_segments}
                label="Segments"
              />
              <StatCard
                value={analytics.counts.total_objects}
                label="Objects"
              />
            </Box>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Storage Statistics
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, mt: 2 }}>
              <StatCard
                value={formatStorageSize(analytics.storage.total_size_bytes)}
                label="Total Storage"
              />
              <StatCard
                value={formatStorageSize(analytics.storage.average_size_bytes)}
                label="Average Size"
              />
            </Box>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Format Breakdown
            </Typography>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 2 }}>
              <StatCard
                value={analytics.formats.video_flows}
                label="Video Flows"
              />
              <StatCard
                value={analytics.formats.audio_flows}
                label="Audio Flows"
              />
              <StatCard
                value={analytics.formats.image_flows}
                label="Image Flows"
              />
              <StatCard
                value={analytics.formats.data_flows}
                label="Data Flows"
              />
              <StatCard
                value={analytics.formats.multi_flows}
                label="Multi Flows"
              />
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

