import React, { useRef, useEffect } from 'react';
import { Box, Typography, Card, CardContent, Tooltip } from '@mui/material';
import { Segment } from '../types';

interface SegmentVideoWidgetProps {
  segment: Segment;
  width?: number;
  height?: number;
}

const SegmentVideoWidget: React.FC<SegmentVideoWidgetProps> = ({ 
  segment, 
  width = 240, 
  height = 135 
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const getFirstPresignedUrl = (seg: Segment) => {
    return seg.get_urls?.find(url => url.presigned && url.url) || seg.get_urls?.[0];
  };

  const getVideoMimeType = (url: string): string => {
    const urlLower = url.toLowerCase();
    if (urlLower.includes('.ts') || urlLower.endsWith('.ts')) {
      return 'video/mp2t';
    } else if (urlLower.includes('.mp4') || urlLower.endsWith('.mp4')) {
      return 'video/mp4';
    } else if (urlLower.includes('.webm') || urlLower.endsWith('.webm')) {
      return 'video/webm';
    } else if (urlLower.includes('.ogg') || urlLower.endsWith('.ogv')) {
      return 'video/ogg';
    } else if (urlLower.includes('.mkv') || urlLower.endsWith('.mkv')) {
      return 'video/x-matroska';
    } else if (urlLower.includes('.m3u8')) {
      return 'application/x-mpegURL';
    }
    return '';
  };

  const firstUrl = getFirstPresignedUrl(segment);
  const timerange = segment.timerange?.value || '-';
  
  // Parse timerange to extract time information for display
  const parseTimerange = (tr: string): { start?: string; end?: string; duration?: string } => {
    if (!tr || tr === '-') return {};
    
    // Match pattern like [10:0_20:0) or [10:0]
    const match = tr.match(/\[?([0-9:-]+)_?([0-9:-]+)?/);
    if (match) {
      const start = match[1];
      const end = match[2];
      return { start, end };
    }
    return {};
  };

  const timeInfo = parseTimerange(timerange);

  // Autoplay video when component mounts
  useEffect(() => {
    if (videoRef.current && firstUrl?.presigned && firstUrl?.url) {
      const video = videoRef.current;
      const playPromise = video.play();
      
      // Handle autoplay promise (browsers may block autoplay without user interaction)
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          // Autoplay was prevented, but video will still load
          console.debug('Video autoplay prevented:', error);
        });
      }
    }
  }, [firstUrl]);

  return (
    <Card 
      sx={{ 
        width, 
        minWidth: width,
        display: 'flex',
        flexDirection: 'column',
        margin: 1,
        '&:hover': {
          boxShadow: 4,
        }
      }}
    >
      <Box sx={{ position: 'relative', width: '100%', backgroundColor: '#000' }}>
        {firstUrl?.presigned && firstUrl?.url ? (
          <video
            ref={videoRef}
            controls
            autoPlay
            muted
            playsInline
            style={{
              width: '100%',
              height: height,
              display: 'block',
            }}
            preload="auto"
            crossOrigin="anonymous"
          >
            {(() => {
              const mimeType = getVideoMimeType(firstUrl.url);
              if (mimeType) {
                return <source src={firstUrl.url} type={mimeType} />;
              } else {
                return (
                  <>
                    <source src={firstUrl.url} type="video/mp2t" />
                    <source src={firstUrl.url} type="video/mp4" />
                    <source src={firstUrl.url} type="video/webm" />
                    <source src={firstUrl.url} />
                  </>
                );
              }
            })()}
            Your browser does not support the video tag.
          </video>
        ) : (
          <Box 
            sx={{ 
              width: '100%', 
              height: height, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#1a1a1a',
              color: '#666'
            }}
          >
            <Typography variant="caption">No media</Typography>
          </Box>
        )}
      </Box>
      <CardContent sx={{ flexGrow: 1, p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Tooltip title={timerange} arrow>
          <Typography 
            variant="caption" 
            sx={{ 
              display: 'block',
              fontFamily: 'monospace',
              fontSize: '0.7rem',
              color: 'text.secondary',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              mb: 0.5
            }}
          >
            {timeInfo.start && timeInfo.end 
              ? `${timeInfo.start} - ${timeInfo.end}`
              : timeInfo.start 
              ? `Start: ${timeInfo.start}`
              : timerange}
          </Typography>
        </Tooltip>
        <Typography 
          variant="caption" 
          sx={{ 
            display: 'block',
            fontFamily: 'monospace',
            fontSize: '0.65rem',
            color: 'text.secondary',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}
        >
          {segment.sample_offset !== null && segment.sample_offset !== undefined 
            ? `Offset: ${segment.sample_offset.toLocaleString()}` 
            : ''}
        </Typography>
        {segment.key_frame_count !== null && segment.key_frame_count !== undefined && (
          <Typography 
            variant="caption" 
            sx={{ 
              display: 'block',
              fontSize: '0.65rem',
              color: 'text.secondary'
            }}
          >
            Key frames: {segment.key_frame_count}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default SegmentVideoWidget;

