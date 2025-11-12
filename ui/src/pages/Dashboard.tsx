import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, CircularProgress, IconButton, Tooltip } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import FolderIcon from '@mui/icons-material/Folder';
import TimelineIcon from '@mui/icons-material/Timeline';
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary';
import StorageIcon from '@mui/icons-material/Storage';
import MovieIcon from '@mui/icons-material/Movie';
import MusicNoteIcon from '@mui/icons-material/MusicNote';
import ImageIcon from '@mui/icons-material/Image';
import DataObjectIcon from '@mui/icons-material/DataObject';
import AppsIcon from '@mui/icons-material/Apps';
import { authService, analyticsService } from '../services/api';
import { AnalyticsSummary } from '../types';
import MetricCard from '../components/MetricCard';
import MetricCardGrid from '../components/MetricCardGrid';

const Dashboard: React.FC = () => {
  const user = authService.getCurrentUser();
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadStatistics = async (forceRefresh: boolean = false) => {
    try {
      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      const summary = await analyticsService.getSummary(forceRefresh).catch(() => null);
      setAnalytics(summary);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadStatistics(false);
  }, []);

  const handleRefresh = () => {
    loadStatistics(true);
  };

  const formatStorageSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Dashboard
        </Typography>
        <Tooltip title="Refresh dashboard data">
          <IconButton 
            onClick={handleRefresh} 
            disabled={loading || refreshing}
            color="primary"
            aria-label="refresh dashboard"
          >
            <RefreshIcon sx={{ 
              animation: refreshing ? 'spin 1s linear infinite' : 'none',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' }
              }
            }} />
          </IconButton>
        </Tooltip>
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
            <MetricCardGrid columns={4} spacing={2} sx={{ mt: 2 }}>
              <MetricCard
                title="Sources"
                value={analytics.counts.total_sources}
                icon={<FolderIcon />}
                color="primary"
                size="medium"
              />
              <MetricCard
                title="Flows"
                value={analytics.counts.total_flows}
                icon={<TimelineIcon />}
                color="secondary"
                size="medium"
              />
              <MetricCard
                title="Segments"
                value={analytics.counts.total_segments}
                icon={<VideoLibraryIcon />}
                color="success"
                size="medium"
              />
              <MetricCard
                title="Objects"
                value={analytics.counts.total_objects}
                icon={<StorageIcon />}
                color="info"
                size="medium"
              />
            </MetricCardGrid>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Storage Statistics
            </Typography>
            <MetricCardGrid columns={2} spacing={2} sx={{ mt: 2 }}>
              <MetricCard
                title="Total Storage"
                value={formatStorageSize(analytics.storage.total_size_bytes)}
                icon={<StorageIcon />}
                color="primary"
                size="medium"
              />
              <MetricCard
                title="Average Size"
                value={formatStorageSize(analytics.storage.average_size_bytes)}
                icon={<StorageIcon />}
                color="secondary"
                size="medium"
              />
            </MetricCardGrid>
          </Box>

          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Format Breakdown
            </Typography>
            <MetricCardGrid columns={5} spacing={2} sx={{ mt: 2 }}>
              <MetricCard
                title="Video Flows"
                value={analytics.formats.video_flows}
                icon={<MovieIcon />}
                color="error"
                size="small"
              />
              <MetricCard
                title="Audio Flows"
                value={analytics.formats.audio_flows}
                icon={<MusicNoteIcon />}
                color="warning"
                size="small"
              />
              <MetricCard
                title="Image Flows"
                value={analytics.formats.image_flows}
                icon={<ImageIcon />}
                color="info"
                size="small"
              />
              <MetricCard
                title="Data Flows"
                value={analytics.formats.data_flows}
                icon={<DataObjectIcon />}
                color="success"
                size="small"
              />
              <MetricCard
                title="Multi Flows"
                value={analytics.formats.multi_flows}
                icon={<AppsIcon />}
                color="secondary"
                size="small"
              />
            </MetricCardGrid>
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

