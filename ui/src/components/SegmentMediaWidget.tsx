import React, { useRef, useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Tooltip, 
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Chip
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import VideoPlayer, { VideoPlayerType } from './VideoPlayer';
import { Segment, Flow } from '../types';

interface SegmentMediaWidgetProps {
  segment: Segment;
  flow?: Flow | null;
  width?: number;
  height?: number;
  isFirst?: boolean; // Flag to indicate if this is the first video (load immediately)
  videoPlayerType?: VideoPlayerType; // Which video player to use: 'videojs', 'react-player', or 'native'
}

type MediaType = 'video' | 'image' | 'audio' | 'data' | 'unknown';

const SegmentMediaWidget: React.FC<SegmentMediaWidgetProps> = ({ 
  segment, 
  flow,
  width = 240, 
  height = 135,
  isFirst = false,
  videoPlayerType = 'native' // Default to native HTML5 for best performance
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [videoLoading, setVideoLoading] = useState(true);
  
  const getFirstPresignedUrl = (seg: Segment) => {
    return seg.get_urls?.find(url => url.presigned && url.url) || seg.get_urls?.[0];
  };

  // Determine media type from flow format and URL
  const getMediaType = (): MediaType => {
    // Always check URL extension first - it's more reliable than format
    const firstUrl = getFirstPresignedUrl(segment);
    if (firstUrl?.url) {
      const urlLower = firstUrl.url.toLowerCase();
      if (urlLower.includes('.mp4') || urlLower.includes('.ts') || urlLower.includes('.webm') ||
          urlLower.includes('.mkv') || urlLower.includes('.avi') || urlLower.includes('.mov') ||
          urlLower.includes('.m3u8') || urlLower.includes('.ogv') || urlLower.includes('.flv') ||
          urlLower.includes('.m4v') || urlLower.includes('.3gp')) {
        return 'video';
      }
      if (urlLower.includes('.jpg') || urlLower.includes('.jpeg') || urlLower.includes('.png') ||
          urlLower.includes('.gif') || urlLower.includes('.webp') || urlLower.includes('.bmp') ||
          urlLower.includes('.tiff') || urlLower.includes('.svg') || urlLower.includes('.ico')) {
        return 'image';
      }
      if (urlLower.includes('.mp3') || urlLower.includes('.aac') || urlLower.includes('.wav') ||
          urlLower.includes('.flac') || urlLower.includes('.ogg') || urlLower.includes('.opus') ||
          urlLower.includes('.m4a') || urlLower.includes('.wma')) {
        return 'audio';
      }
    }

    // Fall back to flow format if URL doesn't help
    if (flow?.format) {
      const formatLower = flow.format.toLowerCase();
      if (formatLower.includes('video') || formatLower.includes('mpeg') || formatLower.includes('mp4') || 
          formatLower.includes('h264') || formatLower.includes('hevc') || formatLower.includes('avc')) {
        return 'video';
      }
      if (formatLower.includes('image') || formatLower.includes('jpeg') || formatLower.includes('jpg') ||
          formatLower.includes('png') || formatLower.includes('gif') || formatLower.includes('tiff') ||
          formatLower.includes('bmp') || formatLower.includes('webp')) {
        return 'image';
      }
      if (formatLower.includes('audio') || formatLower.includes('aac') || formatLower.includes('mp3') ||
          formatLower.includes('wav') || formatLower.includes('flac') || formatLower.includes('opus')) {
        return 'audio';
      }
      if (formatLower.includes('data') || formatLower.includes('json') || formatLower.includes('xml') ||
          formatLower.includes('text') || formatLower.includes('binary')) {
        return 'data';
      }
    }

    // If we have a URL but can't determine type, try to render as video (most common case)
    if (firstUrl?.url) {
      // Check if URL looks like it could be media (has common media query params or paths)
      const urlLower = firstUrl.url.toLowerCase();
      if (urlLower.includes('video') || urlLower.includes('media') || urlLower.includes('stream')) {
        return 'video';
      }
    }

    return 'unknown';
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

  const getAudioMimeType = (url: string): string => {
    const urlLower = url.toLowerCase();
    if (urlLower.includes('.mp3') || urlLower.endsWith('.mp3')) {
      return 'audio/mpeg';
    } else if (urlLower.includes('.aac') || urlLower.endsWith('.aac')) {
      return 'audio/aac';
    } else if (urlLower.includes('.wav') || urlLower.endsWith('.wav')) {
      return 'audio/wav';
    } else if (urlLower.includes('.flac') || urlLower.endsWith('.flac')) {
      return 'audio/flac';
    } else if (urlLower.includes('.ogg') || urlLower.endsWith('.ogg')) {
      return 'audio/ogg';
    } else if (urlLower.includes('.opus') || urlLower.endsWith('.opus')) {
      return 'audio/opus';
    } else if (urlLower.includes('.m4a') || urlLower.endsWith('.m4a')) {
      return 'audio/mp4';
    }
    return '';
  };

  const firstUrl = getFirstPresignedUrl(segment);
  const timerange = segment.timerange?.value || '-';
  const mediaType = getMediaType();
  
  // Debug logging for video playback issues
  useEffect(() => {
    if (mediaType === 'video') {
      console.debug('Segment video debug:', {
        hasGetUrls: !!segment.get_urls,
        getUrlsLength: segment.get_urls?.length || 0,
        firstUrl: firstUrl,
        objectId: segment.object_id,
        timerange: timerange
      });
    }
  }, [segment, mediaType, firstUrl, timerange]);
  
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

  // Handle video loading state
  useEffect(() => {
    if (mediaType === 'video' && firstUrl?.url && isFirst) {
      // First video: show loading indicator
      setVideoLoading(true);
    }
  }, [firstUrl?.url, mediaType, isFirst]);

  const renderMediaContent = () => {
    // Check if we have URLs available
    if (!segment.get_urls || segment.get_urls.length === 0) {
      return (
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
          <Typography variant="caption">No URLs available</Typography>
        </Box>
      );
    }
    
    // Allow non-presigned URLs too - they might still work for video playback
    if (!firstUrl?.url) {
      return (
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
          <Typography variant="caption">No valid URL</Typography>
        </Box>
      );
    }

    switch (mediaType) {
      case 'video':
        return (
          <VideoPlayer
            src={firstUrl.url}
            width="100%"
            height={height}
            controls
            muted
            playsInline
            preload={isFirst ? 'auto' : 'metadata'}
            playerType={videoPlayerType}
            light={!isFirst && videoPlayerType === 'react-player'} // Light mode for non-first videos with react-player
            playIcon={
              <Box
                sx={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(0, 0, 0, 0.5)',
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                <Typography variant="h4">▶</Typography>
              </Box>
            }
            onReady={() => {
              if (isFirst) {
                setVideoLoading(false);
              }
            }}
            onError={(error) => {
              console.error('Video playback error:', {
                error,
                url: firstUrl.url,
                playerType: videoPlayerType
              });
              if (isFirst) {
                setVideoLoading(false);
              }
            }}
            onLoadStart={() => {
              if (isFirst) {
                setVideoLoading(true);
              }
            }}
          />
        );

      case 'image':
        return (
          <Box
            component="img"
            src={firstUrl.url}
            alt="Segment"
            loading="lazy"
            sx={{
              width: '100%',
              height: height,
              objectFit: 'contain',
              backgroundColor: '#000',
              display: 'block',
            }}
          />
        );

      case 'audio':
        return (
          <Box sx={{ 
            width: '100%', 
            height: height, 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center',
            backgroundColor: '#1a1a1a',
            color: '#fff',
            p: 2
          }}>
            <audio
              ref={audioRef}
              controls
              style={{
                width: '100%',
                maxWidth: '100%',
              }}
              preload="none"
            >
              {(() => {
                const mimeType = getAudioMimeType(firstUrl.url);
                if (mimeType) {
                  return <source src={firstUrl.url} type={mimeType} />;
                } else {
                  return (
                    <>
                      <source src={firstUrl.url} type="audio/mpeg" />
                      <source src={firstUrl.url} type="audio/mp4" />
                      <source src={firstUrl.url} type="audio/ogg" />
                      <source src={firstUrl.url} />
                    </>
                  );
                }
              })()}
              Your browser does not support the audio tag.
            </audio>
          </Box>
        );

      case 'data':
        return (
          <Box 
            sx={{ 
              width: '100%', 
              height: height, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#1a1a1a',
              color: '#888',
              p: 2,
              flexDirection: 'column',
              gap: 1
            }}
          >
            <Typography variant="h6" sx={{ fontSize: '2rem' }}>📄</Typography>
            <Typography variant="caption" sx={{ textAlign: 'center' }}>
              Data File
            </Typography>
          </Box>
        );

      default:
        // For unknown types, try to render as video if we have a URL (browsers can often handle it)
        if (firstUrl?.url) {
          return (
            <VideoPlayer
              src={firstUrl.url}
              width="100%"
              height={height}
              controls
              muted
              playsInline
              preload="metadata"
              playerType={videoPlayerType}
              onError={(error) => {
                console.debug('Video playback error (unknown format):', {
                  error,
                  url: firstUrl.url,
                  format: flow?.format
                });
              }}
            />
          );
        }
        return (
          <Box 
            sx={{ 
              width: '100%', 
              height: height, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#1a1a1a',
              color: '#888',
              p: 2,
              flexDirection: 'column',
              gap: 1
            }}
          >
            <Typography variant="h6" sx={{ fontSize: '2rem' }}>📦</Typography>
            <Typography variant="caption" sx={{ textAlign: 'center' }}>
              {flow?.format || 'Unknown Format'}
            </Typography>
            {!firstUrl?.url && (
              <Typography variant="caption" sx={{ textAlign: 'center', fontSize: '0.6rem', color: '#666' }}>
                No URL available
              </Typography>
            )}
          </Box>
        );
    }
  };

  return (
    <>
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
        {renderMediaContent()}
      </Box>
      <CardContent sx={{ flexGrow: 1, p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
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
                flex: 1
              }}
            >
              {timeInfo.start && timeInfo.end 
                ? `${timeInfo.start} - ${timeInfo.end}`
                : timeInfo.start 
                ? `Start: ${timeInfo.start}`
                : timerange}
            </Typography>
          </Tooltip>
          <IconButton
            size="small"
            onClick={() => setInfoModalOpen(true)}
            sx={{
              ml: 1,
              color: 'text.secondary',
              '&:hover': {
                color: 'primary.main',
                backgroundColor: 'action.hover',
              },
            }}
          >
            <InfoIcon fontSize="small" />
          </IconButton>
        </Box>
        <Typography 
          variant="caption" 
          sx={{ 
            display: 'block',
            fontFamily: 'monospace',
            fontSize: '0.65rem',
            color: 'text.secondary',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            mb: 0.5
          }}
        >
          Type: {mediaType}
        </Typography>
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

    {/* Segment Info Modal */}
    <Dialog 
      open={infoModalOpen} 
      onClose={() => setInfoModalOpen(false)} 
      maxWidth="md" 
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Segment Details</Typography>
          <Chip label={mediaType} color="primary" size="small" />
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          <Stack spacing={2}>
            {/* Basic Information */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Basic Information
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Object ID</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                        {segment.object_id}
                      </TableCell>
                    </TableRow>
                    {segment.timerange && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Time Range</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace' }}>
                          {segment.timerange.value}
                        </TableCell>
                      </TableRow>
                    )}
                    {segment.ts_offset && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Timestamp Offset</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace' }}>
                          {segment.ts_offset.value}
                        </TableCell>
                      </TableRow>
                    )}
                    {segment.last_duration && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Last Duration</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace' }}>
                          {segment.last_duration.value}
                        </TableCell>
                      </TableRow>
                    )}
                    {segment.sample_offset !== null && segment.sample_offset !== undefined && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Sample Offset</TableCell>
                        <TableCell>
                          {segment.sample_offset.toLocaleString()}
                        </TableCell>
                      </TableRow>
                    )}
                    {segment.sample_count !== null && segment.sample_count !== undefined && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Sample Count</TableCell>
                        <TableCell>
                          {segment.sample_count.toLocaleString()}
                        </TableCell>
                      </TableRow>
                    )}
                    {segment.key_frame_count !== null && segment.key_frame_count !== undefined && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Key Frame Count</TableCell>
                        <TableCell>
                          {segment.key_frame_count}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>

            {/* Flow Information */}
            {flow && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Flow Information
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '40%' }}>Flow ID</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                          {flow.id}
                        </TableCell>
                      </TableRow>
                      {flow.label && (
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold' }}>Label</TableCell>
                          <TableCell>{flow.label}</TableCell>
                        </TableRow>
                      )}
                      {flow.format && (
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold' }}>Format</TableCell>
                          <TableCell>{flow.format}</TableCell>
                        </TableRow>
                      )}
                      {flow.container && (
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold' }}>Container</TableCell>
                          <TableCell>{flow.container}</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            )}

            {/* URLs */}
            {segment.get_urls && segment.get_urls.length > 0 && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  URLs ({segment.get_urls.length})
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Stack spacing={1}>
                  {segment.get_urls.map((url, index) => (
                    <Box key={index} sx={{ p: 1, backgroundColor: '#e8e8e8', borderRadius: 1 }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                        {url.url}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                        {url.presigned && (
                          <Chip label="Presigned" size="small" color="success" />
                        )}
                        {url.label && (
                          <Chip label={`Label: ${url.label}`} size="small" />
                        )}
                        {url.storage_id && (
                          <Chip 
                            label={`Storage: ${url.storage_id.substring(0, 8)}...`} 
                            size="small" 
                            sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                          />
                        )}
                      </Box>
                    </Box>
                  ))}
                </Stack>
              </Paper>
            )}
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setInfoModalOpen(false)}>Close</Button>
      </DialogActions>
    </Dialog>
    </>
  );
};

export default SegmentMediaWidget;

