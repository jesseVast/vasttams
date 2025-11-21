import React from 'react';
import { Box, Typography } from '@mui/material';

interface VideoTextOverlayProps {
  text: string;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

/**
 * Modern, semi-transparent, grayscale text overlay for video players
 */
const VideoTextOverlay: React.FC<VideoTextOverlayProps> = ({ 
  text, 
  position = 'top-right' 
}) => {
  if (!text) return null;

  const positionStyles = {
    'top-left': {
      top: 8,
      left: 8,
      right: 'auto',
      bottom: 'auto',
    },
    'top-right': {
      top: 8,
      right: 8,
      left: 'auto',
      bottom: 'auto',
    },
    'bottom-left': {
      bottom: 8,
      left: 8,
      right: 'auto',
      top: 'auto',
    },
    'bottom-right': {
      bottom: 8,
      right: 8,
      left: 'auto',
      top: 'auto',
    },
  };

  return (
    <Box
      sx={{
        position: 'absolute',
        ...positionStyles[position],
        maxWidth: 'calc(100% - 100px)', // Ensure it doesn't go off screen
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(4px)',
        color: '#fff',
        padding: '6px 12px',
        borderRadius: 1,
        fontSize: '12px',
        fontFamily: 'monospace',
        zIndex: 1000,
        pointerEvents: 'none',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        // Grayscale effect
        filter: 'grayscale(100%)',
        // Modern styling
        border: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      <Typography 
        variant="body2" 
        sx={{ 
          fontSize: '12px', 
          lineHeight: 1.3,
          color: '#e0e0e0', // Light gray text
          fontWeight: 400,
        }}
      >
        {text}
      </Typography>
    </Box>
  );
};

export default VideoTextOverlay;

