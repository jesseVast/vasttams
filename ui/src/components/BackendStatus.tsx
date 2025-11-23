import React, { useState, useEffect, useCallback } from 'react';
import {
  Chip,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import { CheckCircle, Error, Warning } from '@mui/icons-material';
import api from '../services/api';

interface BackendStatusProps {
  size?: 'small' | 'medium';
}

const BackendStatus: React.FC<BackendStatusProps> = ({ size = 'small' }) => {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline' | 'error'>('checking');
  const [lastChecked, setLastChecked] = useState<Date>(new Date());

  const checkBackendStatus = useCallback(async () => {
    try {
      // Use the /health endpoint which doesn't require authentication
      // Health endpoint is at root level, not under API path
      // Always use absolute URL for health check
      const healthUrl = typeof window !== 'undefined' 
        ? `${window.location.origin}/health`
        : '/health';
      
      // Use fetch directly to bypass axios baseURL
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      
      setStatus('online');
      setLastChecked(new Date());
    } catch (error: any) {
      // If it's a timeout or network error, mark as offline
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        // Timeout - server might be busy but still online
        // Keep previous status if it was online, only change if it was offline
        setStatus((prev) => prev === 'online' ? 'online' : 'offline');
      } else if (error.response) {
        // If we got a response (even an error like 500), backend is online
        // Only mark as offline if it's a network error (no response)
        setStatus('online');
        setLastChecked(new Date());
      } else {
        // Network error (CORS, connection refused, etc.)
        setStatus('offline');
        setLastChecked(new Date());
      }
    }
  }, []);

  useEffect(() => {
    // Check immediately
    checkBackendStatus();
    
    // Check every 15 seconds (more frequent updates)
    // Use shorter interval for better responsiveness during video playback
    const interval = setInterval(() => {
      // Always update lastChecked to show widget is active
      setLastChecked(new Date());
      checkBackendStatus();
    }, 15000);
    
    return () => clearInterval(interval);
  }, [checkBackendStatus]);

  const getStatusIcon = () => {
    switch (status) {
      case 'checking':
        return <CircularProgress size={16} color="inherit" />;
      case 'online':
        return <CheckCircle fontSize="small" />;
      case 'offline':
        return <Warning fontSize="small" />;
      case 'error':
        return <Error fontSize="small" />;
      default:
        return <Error fontSize="small" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'online':
        return 'success';
      case 'offline':
        return 'warning';
      case 'error':
        return 'error';
      case 'checking':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'checking':
        return 'Checking';
      case 'online':
        return 'Online';
      case 'offline':
        return 'Offline';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  const getTooltipText = () => {
    const timeStr = lastChecked.toLocaleTimeString();
    const timeAgo = Math.floor((Date.now() - lastChecked.getTime()) / 1000);
    const timeAgoStr = timeAgo < 60 ? `${timeAgo}s ago` : `${Math.floor(timeAgo / 60)}m ago`;
    return `API Status: ${getStatusText()}\nLast checked: ${timeStr} (${timeAgoStr})`;
  };

  const handleClick = () => {
    // Force recheck of backend status
    setStatus('checking');
    checkBackendStatus();
  };

  return (
    <Tooltip title={getTooltipText()} arrow>
      <Chip
        icon={getStatusIcon()}
        label={getStatusText()}
        color={getStatusColor() as any}
        size="small"
        variant="outlined"
        onClick={handleClick}
        sx={{
          cursor: 'pointer',
          fontWeight: 500,
          fontSize: '0.75rem',
          height: 28,
          backgroundColor: (() => {
            switch (status) {
              case 'online': return '#ffffff';
              case 'offline': return '#fff3e0';
              case 'error': return '#ffebee';
              case 'checking': return '#e3f2fd';
              default: return undefined;
            }
          })(),
          color: (() => {
            switch (status) {
              case 'online': return '#2e7d32';
              case 'offline': return '#ef6c00';
              case 'error': return '#c62828';
              case 'checking': return '#1565c0';
              default: return undefined;
            }
          })(),
          borderColor: (() => {
            switch (status) {
              case 'online': return '#4caf50';
              case 'offline': return '#ff9800';
              case 'error': return '#f44336';
              case 'checking': return '#2196f3';
              default: return undefined;
            }
          })(),
          '&:hover': {
            transform: 'scale(1.02)',
            transition: 'transform 0.2s ease-in-out',
            backgroundColor: (() => {
              switch (status) {
                case 'online': return '#f1f8e9';
                case 'offline': return '#fff8e1';
                case 'error': return '#fce4ec';
                case 'checking': return '#e8f5e8';
                default: return undefined;
              }
            })(),
          },
          '& .MuiChip-icon': {
            color: (() => {
              switch (status) {
                case 'online': return '#4caf50';
                case 'offline': return '#ff9800';
                case 'error': return '#f44336';
                case 'checking': return '#2196f3';
                default: return undefined;
              }
            })(),
            fontSize: '16px',
          },
        }}
      />
    </Tooltip>
  );
};

export default BackendStatus;

