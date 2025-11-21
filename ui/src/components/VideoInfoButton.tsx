import React from 'react';
import { Box, Tooltip } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';

interface VideoInfoButtonProps {
  onClick: () => void;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  tooltip?: string;
}

/**
 * Modern, semi-transparent info button overlay for video players
 */
const VideoInfoButton: React.FC<VideoInfoButtonProps> = ({ 
  onClick, 
  position = 'top-left',
  tooltip = 'Segment Info'
}) => {
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
        zIndex: 1000,
      }}
    >
      <Tooltip title={tooltip}>
        <Box
          onClick={onClick}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: 'rgba(255, 255, 255, 0.8)',
            padding: '4px',
            borderRadius: '4px',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              color: '#fff',
            },
          }}
        >
          <InfoIcon sx={{ fontSize: '18px' }} />
        </Box>
      </Tooltip>
    </Box>
  );
};

export default VideoInfoButton;

