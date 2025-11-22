import React from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import InfoIcon from '@mui/icons-material/Info';

interface VideoControlsWidgetProps {
  isPlaying: boolean;
  onPlay: () => void;
  onPause: () => void;
  onStop: () => void;
  onInfoClick?: () => void;
  timerange?: string;
  segmentIndex?: number;
}

/**
 * Video controls widget displayed below the video player
 * Contains play, pause, stop buttons and info button
 */
const VideoControlsWidget: React.FC<VideoControlsWidgetProps> = ({
  isPlaying,
  onPlay,
  onPause,
  onStop,
  onInfoClick,
  timerange,
  segmentIndex,
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 1,
        padding: '8px 12px',
        backgroundColor: '#424242', // Dark gray
        borderRadius: 1,
        marginTop: '4px',
        minHeight: '40px',
      }}
    >
      {/* Left side: Timerange */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
        {timerange && timerange !== '-' && (
          <Box
            sx={{
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              color: '#fff',
              padding: '4px 8px',
              borderRadius: 0.5,
              fontSize: '11px',
              fontFamily: 'monospace',
              whiteSpace: 'nowrap',
            }}
          >
            {timerange}
          </Box>
        )}
      </Box>

      {/* Middle: Control buttons */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: 'center', flex: 1 }}>
        {isPlaying ? (
          <Tooltip title="Pause">
            <IconButton
              size="small"
              onClick={onPause}
              sx={{
                color: '#fff',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
              }}
            >
              <PauseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ) : (
          <Tooltip title="Play">
            <IconButton
              size="small"
              onClick={onPlay}
              sx={{
                color: '#fff',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
              }}
            >
              <PlayArrowIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        <Tooltip title="Stop">
          <IconButton
            size="small"
            onClick={onStop}
            sx={{
              color: '#fff',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            <StopIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Right side: Info button */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1, justifyContent: 'flex-end' }}>
        {onInfoClick && (
          <Tooltip title="Segment Info">
            <IconButton
              size="small"
              onClick={onInfoClick}
              sx={{
                color: '#fff',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
              }}
            >
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );
};

export default VideoControlsWidget;

