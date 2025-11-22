import React, { useRef, useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Card, 
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
import VideoPlayer, { VideoPlayerType } from './VideoPlayer';
import VideoControlsWidget from './VideoControlsWidget';
import { Segment, Flow } from '../types';
import { API_BASE_URL, API_PREFIX } from '../services/api';

interface SegmentMediaWidgetProps {
  segment: Segment;
  flow?: Flow | null;
  width?: number;
  height?: number;
  isFirst?: boolean; // Flag to indicate if this is the first video (load immediately)
  videoPlayerType?: VideoPlayerType; // Which video player to use: 'videojs', 'react-player', or 'native'
  autoPlayEnabled?: boolean;
  segmentIndex?: number;
}

type MediaType = 'video' | 'image' | 'audio' | 'data' | 'unknown';

const SegmentMediaWidget: React.FC<SegmentMediaWidgetProps> = ({ 
  segment, 
  flow,
  width = 240, 
  height = 135,
  isFirst = false,
  videoPlayerType = 'native', // Default to native HTML5 for best performance
  autoPlayEnabled = false,
  segmentIndex
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const videoPlayerRef = useRef<any>(null);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [isInViewport, setIsInViewport] = useState(isFirst); // First video loads immediately
  const [intersectionRatio, setIntersectionRatio] = useState(0); // Track how much is visible
  const [wasPlayingBeforeModal, setWasPlayingBeforeModal] = useState<boolean>(false);
  const [shouldLoadVideo, setShouldLoadVideo] = useState(isFirst); // Track if video should be loaded
  const [shouldUnloadVideo, setShouldUnloadVideo] = useState(false); // Track if video should be unloaded
  const [retryWithMpegts, setRetryWithMpegts] = useState(false); // Track if we should retry with mpegts.js after native player error
  const [isVideoPlaying, setIsVideoPlaying] = useState(false); // Track if video is actually playing
  const [isVideoCompleted, setIsVideoCompleted] = useState(false); // Track if video has completed
  
  const getFirstPresignedUrl = (seg: Segment) => {
    return seg.get_urls?.find(url => url.presigned && url.url) || seg.get_urls?.[0];
  };

  // Convert URLs to proxy URLs for CORS support (especially needed for mpegts.js)
  const getProxyUrl = (originalUrl: string): string => {
    if (!flow?.id || !segment.object_id) {
      console.warn('[SegmentMediaWidget] Cannot create proxy URL: missing flow.id or segment.object_id');
      return originalUrl;
    }
    
    // Always use proxy endpoint for CORS support when proxying
    // This is especially important for mpegts.js which needs to fetch the video data
    const baseUrl = API_BASE_URL.replace(/\/$/, '');
    const apiPrefix = API_PREFIX.replace(/\/$/, '');
    const encodedUrl = encodeURIComponent(originalUrl);
    
    // Include token in query parameter for authentication (like HLS playlists)
    let proxyUrl = `${baseUrl}${apiPrefix}/hls/flows/${flow.id}/segments/${segment.object_id}?url=${encodedUrl}`;
    
    if (typeof window !== 'undefined' && window.localStorage) {
      const token = localStorage.getItem('token');
      if (token) {
        proxyUrl += `&access_token=${encodeURIComponent(token)}`;
      }
    }
    
    console.debug(`[Segment ${segmentIndex}] Proxying URL:`, {
      original: originalUrl.substring(0, 100),
      proxy: proxyUrl.substring(0, 150)
    });
    
    return proxyUrl;
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
  


  // Setup IntersectionObserver for lazy loading and scroll-based playback
  useEffect(() => {
    if (!cardRef.current || mediaType !== 'video') return;

    const container = document.getElementById('segments-container');
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const ratio = entry.intersectionRatio;
          const isVisible = entry.isIntersecting && ratio > 0.1;
          
          console.debug(`[Segment ${segmentIndex}] Viewport visibility:`, isVisible, 'ratio:', ratio);
          
          setIsInViewport(isVisible);
          setIntersectionRatio(ratio);
          
          // Load video when it comes into viewport (with some margin)
          // Ensure videos load in sequence by checking if previous videos are loaded
          if (isVisible && !shouldLoadVideo) {
            // For sequential loading: only load if this is the first video or previous video is loaded
            if (segmentIndex === undefined || segmentIndex === 0) {
              setShouldLoadVideo(true);
              setShouldUnloadVideo(false);
            } else {
              // Check if previous video card exists and is loaded
              const prevCard = container.querySelector(`[data-segment-index="${segmentIndex - 1}"]`);
              if (prevCard) {
                const prevVideo = prevCard.querySelector('video');
                // Load if previous video is loaded or doesn't exist
                if (!prevVideo || prevVideo.readyState >= 2) {
                  setShouldLoadVideo(true);
                  setShouldUnloadVideo(false);
                } else {
                  // Wait for previous video to load
                  const checkPrevVideo = setInterval(() => {
                    if (prevVideo && prevVideo.readyState >= 2) {
                      setShouldLoadVideo(true);
                      setShouldUnloadVideo(false);
                      clearInterval(checkPrevVideo);
                    }
                  }, 100);
                  // Timeout after 5 seconds
                  setTimeout(() => clearInterval(checkPrevVideo), 5000);
                }
              } else {
                // Previous card doesn't exist, safe to load
                setShouldLoadVideo(true);
                setShouldUnloadVideo(false);
              }
            }
          }
          
          // Unload video when it's far from viewport (save resources)
          if (!isVisible && shouldLoadVideo && ratio === 0) {
            // Only unload if it's been out of view for a bit (debounce)
            const unloadTimer = setTimeout(() => {
              if (!entry.isIntersecting) {
                setShouldUnloadVideo(true);
              }
            }, 2000); // 2 second delay before unloading
            
            return () => clearTimeout(unloadTimer);
          } else if (isVisible) {
            setShouldUnloadVideo(false);
          }
        });
      },
      {
        root: container,
        rootMargin: '300px', // Start loading 300px before entering viewport
        threshold: [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1] // More granular thresholds
      }
    );

    observer.observe(cardRef.current);

    return () => {
      observer.disconnect();
    };
  }, [mediaType, segmentIndex, shouldLoadVideo]);

  // Handle scroll-based playback: play only when highly visible, pause otherwise
  useEffect(() => {
    if (mediaType !== 'video' || !shouldLoadVideo || shouldUnloadVideo) return;
    
    // Small delay to ensure ref is set
    const timer = setTimeout(() => {
      if (videoPlayerRef.current) {
        const player = videoPlayerRef.current;
        const videoElement = player.getVideoElement?.();
        
        // Only play if:
        // 1. Auto-play is enabled
        // 2. Video is in viewport
        // 3. At least 50% of the video is visible (to prioritize the most visible video)
        const shouldPlay = autoPlayEnabled && isInViewport && intersectionRatio >= 0.5;
        
        if (shouldPlay) {
          // Play when highly visible
          console.debug(`[Segment ${segmentIndex}] Attempting to play video (ratio: ${intersectionRatio.toFixed(2)})`);
          if (player.play && typeof player.play === 'function') {
            player.play()
              .then(() => {
                // Verify video actually started playing after play() resolves
                setTimeout(() => {
                  if (videoElement) {
                    const actuallyPlaying = !videoElement.paused && videoElement.readyState >= 2;
                    if (actuallyPlaying) {
                      console.debug(`[Segment ${segmentIndex}] Video successfully started playing`);
                    } else {
                      console.warn(`[Segment ${segmentIndex}] play() resolved but video not actually playing (paused: ${videoElement.paused}, readyState: ${videoElement.readyState})`);
                    }
                  }
                }, 200);
              })
              .catch((error: any) => {
                console.debug(`[Segment ${segmentIndex}] Video autoplay prevented:`, error);
              });
          }
        } else {
          // Pause when not highly visible or out of viewport
          if (videoElement && !videoElement.paused) {
            console.debug(`[Segment ${segmentIndex}] Pausing video (ratio: ${intersectionRatio.toFixed(2)}, autoPlay: ${autoPlayEnabled})`);
            if (player.pause && typeof player.pause === 'function') {
              player.pause();
              setIsVideoPlaying(false);
              // Reset playback to start when leaving viewport (optional - for better UX)
              if (!isInViewport && videoElement) {
                videoElement.currentTime = 0;
              }
            }
          }
        }
      }
    }, 150);
    
    return () => clearTimeout(timer);
  }, [autoPlayEnabled, isInViewport, intersectionRatio, mediaType, segmentIndex, shouldLoadVideo, shouldUnloadVideo]);

  // Periodically sync video playing state with actual video element state
  // This is important for mpegts videos which might show first frame but not actually play
  useEffect(() => {
    if (mediaType !== 'video' || !shouldLoadVideo || shouldUnloadVideo) return;
    
    const syncInterval = setInterval(() => {
      if (videoPlayerRef.current) {
        const videoElement = videoPlayerRef.current.getVideoElement?.();
        if (videoElement) {
          const actuallyPlaying = !videoElement.paused && videoElement.readyState >= 2;
          if (actuallyPlaying !== isVideoPlaying) {
            console.debug(`[Segment ${segmentIndex}] Syncing playing state: ${isVideoPlaying} -> ${actuallyPlaying} (paused: ${videoElement.paused}, readyState: ${videoElement.readyState})`);
            setIsVideoPlaying(actuallyPlaying);
          }
        }
      }
    }, 500); // Check every 500ms
    
    return () => clearInterval(syncInterval);
  }, [mediaType, shouldLoadVideo, shouldUnloadVideo, segmentIndex, isVideoPlaying]);

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
        // Auto-detect video format and choose appropriate player
        // Check multiple indicators: URL extension, flow container, and flow format
        const urlLower = firstUrl.url.toLowerCase();
        const containerLower = flow?.container?.toLowerCase() || '';
        const formatLower = flow?.format?.toLowerCase() || '';
        
        // Detect MPEG-TS files (use hls.js instead of mpegts.js)
        const isTSFile = 
          urlLower.includes('.ts') || 
          urlLower.endsWith('.ts') || 
          urlLower.includes('transport') || 
          urlLower.includes('mpegts') ||
          containerLower.includes('mp2t') ||
          containerLower.includes('mpegts') ||
          containerLower.includes('ts') ||
          formatLower.includes('mpegts') ||
          formatLower.includes('transport');
        
        // Detect unsupported formats that native player can't handle
        // MKV, WebM, and other formats may need special handling
        const isUnsupportedFormat = 
          containerLower.includes('matroska') ||
          containerLower.includes('mkv') ||
          containerLower.includes('webm') ||
          urlLower.includes('.mkv') ||
          urlLower.includes('.webm');
        
        // Use mpegts.js for individual .ts segment files
        // Note: hls.js requires HLS playlists (.m3u8), not individual .ts files
        // For individual segments, mpegts.js is the correct choice
        // For unsupported formats, try video.js if available, otherwise fall back to native
        let actualPlayerType: VideoPlayerType;
        if (isTSFile || retryWithMpegts) {
          actualPlayerType = 'mpegts'; // Use mpegts.js for individual .ts files
        } else if (isUnsupportedFormat && videoPlayerType !== 'native') {
          // Try the specified player type (video.js or react-player) for unsupported formats
          actualPlayerType = videoPlayerType;
        } else {
          actualPlayerType = videoPlayerType;
        }
        
        // For mpegts.js player, always use proxy URL for CORS support
        // For other players, use proxy only if it's a .ts file
        const needsProxy = actualPlayerType === 'mpegts' || isTSFile;
        const videoUrl = needsProxy ? getProxyUrl(firstUrl.url) : firstUrl.url;
        
        console.debug(`[Segment ${segmentIndex}] Video player detection:`, {
          actualPlayerType,
          isTSFile,
          isUnsupportedFormat,
          retryWithMpegts,
          urlCheck: urlLower.includes('.ts') || urlLower.includes('transport') || urlLower.includes('mpegts'),
          containerCheck: containerLower.includes('mp2t') || containerLower.includes('mpegts') || containerLower.includes('ts') || containerLower.includes('matroska'),
          formatCheck: formatLower.includes('mpegts') || formatLower.includes('transport'),
          container: flow?.container,
          format: flow?.format,
          url: videoUrl.substring(0, 100)
        });
        
        // Show placeholder until video should be loaded, or unload if far from viewport
        if (!shouldLoadVideo || shouldUnloadVideo) {
          return (
            <Box sx={{ position: 'relative', width: '100%', height: height, backgroundColor: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Box
                sx={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  color: '#fff',
                }}
              >
                <Typography variant="body2" sx={{ opacity: 0.5 }}>
                  Loading...
                </Typography>
              </Box>
              {/* Timerange Overlay - Show even in placeholder */}
              {timerange && timerange !== '-' && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 8,
                    left: 8,
                    backgroundColor: 'rgba(0, 0, 0, 0.6)',
                    color: '#fff',
                    padding: '6px 10px',
                    borderRadius: 1,
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    zIndex: 1000,
                    pointerEvents: 'none',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.5)',
                  }}
                >
                  <Typography variant="body2" sx={{ fontSize: '12px', lineHeight: 1.2 }}>
                    {timerange}
                  </Typography>
                </Box>
              )}
            </Box>
          );
        }
        
        // Don't render VideoPlayer if it should be unloaded - show placeholder instead
        if (shouldUnloadVideo) {
          return (
            <Box sx={{ position: 'relative', width: '100%', height: height, backgroundColor: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Box
                sx={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  color: '#fff',
                }}
              >
                <Typography variant="body2" sx={{ opacity: 0.5 }}>
                  Unloaded
                </Typography>
              </Box>
            </Box>
          );
        }
        
        return (
          <Box sx={{ width: '100%' }}>
            <Box sx={{ position: 'relative', width: '100%', height: height }}>
              <VideoPlayer
                ref={videoPlayerRef}
                src={videoUrl}
                width="100%"
                height={height}
                controls={false}
                muted
                playsInline
                preload={isFirst ? 'auto' : shouldLoadVideo ? 'metadata' : 'none'}
                playerType={actualPlayerType}
                light={!isFirst && actualPlayerType === 'react-player'}
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
                  // Video is ready
                }}
                onPlay={() => {
                  // Verify video is actually playing before setting state
                  if (videoPlayerRef.current) {
                    const videoElement = videoPlayerRef.current.getVideoElement?.();
                    if (videoElement && !videoElement.paused && videoElement.readyState >= 2) {
                      setIsVideoPlaying(true);
                      setIsVideoCompleted(false);
                      console.debug(`[Segment ${segmentIndex}] Video actually started playing`);
                    } else {
                      console.debug(`[Segment ${segmentIndex}] onPlay fired but video not actually playing (paused: ${videoElement?.paused}, readyState: ${videoElement?.readyState})`);
                    }
                  }
                }}
                onEnded={() => {
                  // Video completed
                  setIsVideoPlaying(false);
                  setIsVideoCompleted(true);
                  console.debug(`[Segment ${segmentIndex}] Video completed`);
                }}
              onError={(error) => {
                // Only log errors if video should be loaded (not during unload/load transitions)
                if (shouldLoadVideo && !shouldUnloadVideo) {
                  // Try to extract more details from the error
                  let errorCode: number | null = null;
                  let errorMessage: string = 'Unknown error';
                  let errorName: string = 'Unknown';
                  
                  // If error is a MediaError, extract details
                  if (error && typeof error === 'object') {
                    const mediaError = error as MediaError;
                    if (mediaError.code !== undefined) {
                      errorCode = mediaError.code;
                      errorMessage = mediaError.message || 'Unknown media error';
                      
                      // Map error codes to names
                      switch (mediaError.code) {
                        case 1:
                          errorName = 'MEDIA_ERR_ABORTED';
                          errorMessage = errorMessage || 'Video loading aborted';
                          break;
                        case 2:
                          errorName = 'MEDIA_ERR_NETWORK';
                          errorMessage = errorMessage || 'Network error while loading video';
                          break;
                        case 3:
                          errorName = 'MEDIA_ERR_DECODE';
                          errorMessage = errorMessage || 'Video decoding error';
                          break;
                        case 4:
                          errorName = 'MEDIA_ERR_SRC_NOT_SUPPORTED';
                          errorMessage = errorMessage || 'Video format not supported';
                          break;
                        default:
                          errorName = 'UNKNOWN_ERROR';
                      }
                    }
                  }
                  
                  // Also try to get error from video element if available
                  if (videoPlayerRef.current) {
                    const videoElement = videoPlayerRef.current.getVideoElement?.();
                    if (videoElement && videoElement.error) {
                      const videoError = videoElement.error;
                      if (videoError.code !== undefined) {
                        errorCode = videoError.code;
                        errorMessage = videoError.message || errorMessage;
                        
                        // Update error name based on video element error
                        switch (videoError.code) {
                          case 1:
                            errorName = 'MEDIA_ERR_ABORTED';
                            break;
                          case 2:
                            errorName = 'MEDIA_ERR_NETWORK';
                            break;
                          case 3:
                            errorName = 'MEDIA_ERR_DECODE';
                            break;
                          case 4:
                            errorName = 'MEDIA_ERR_SRC_NOT_SUPPORTED';
                            break;
                        }
                      }
                    }
                  }
                  
                  // Check if this is a known unsupported format that native player can't handle
                  const containerLower = flow?.container?.toLowerCase() || '';
                  const isKnownUnsupported = 
                    containerLower.includes('matroska') ||
                    containerLower.includes('mkv') ||
                    (containerLower.includes('webm') && !containerLower.includes('mp4'));
                  
                  // Log detailed error information
                  // For known unsupported formats, use debug level instead of error
                  if (isKnownUnsupported && errorCode === 4) {
                    console.debug(`[Segment ${segmentIndex}] Native player doesn't support ${flow?.container || 'format'} (expected - format requires video.js or react-player):`, {
                      container: flow?.container,
                      format: flow?.format,
                      segmentId: segment.object_id
                    });
                  } else {
                    console.error('Video playback error:', {
                      errorName,
                      errorCode,
                      errorMessage,
                      url: videoUrl.substring(0, 100) + (videoUrl.length > 100 ? '...' : ''),
                      fullUrl: videoUrl,
                      playerType: actualPlayerType,
                      segmentIndex,
                      segmentId: segment.object_id,
                      flowId: flow?.id,
                      container: flow?.container,
                      format: flow?.format
                    });
                  }
                  
                  // If native player fails with MEDIA_ERR_SRC_NOT_SUPPORTED, try alternative players
                  if (errorCode === 4 && actualPlayerType === 'native' && !retryWithMpegts) {
                    // Check if it might be a TS file that should use mpegts.js
                    const containerLower = flow?.container?.toLowerCase() || '';
                    const formatLower = flow?.format?.toLowerCase() || '';
                    const urlLower = firstUrl.url.toLowerCase();
                    const mightBeTS = 
                      containerLower.includes('mp2t') || 
                      containerLower.includes('mpegts') ||
                      formatLower.includes('mpegts') ||
                      formatLower.includes('transport') ||
                      urlLower.includes('transport') ||
                      urlLower.includes('mpegts') ||
                      urlLower.includes('.ts');
                    
                    if (mightBeTS) {
                      console.warn(`[Segment ${segmentIndex}] Native player doesn't support format, retrying with mpegts.js (detected possible TS format)`);
                      setRetryWithMpegts(true);
                    } else {
                      // For other unsupported formats (like MKV, WebM), log but don't retry with mpegts.js
                      // as mpegts.js only works with MPEG-TS streams
                      console.warn(`[Segment ${segmentIndex}] Native player doesn't support format (${flow?.container || 'unknown'}). Format may require video.js or react-player.`);
                    }
                  }
                } else {
                  console.debug('Video error during load/unload transition (ignored):', {
                    shouldLoadVideo,
                    shouldUnloadVideo,
                    segmentIndex
                  });
                }
              }}
              onLoadStart={() => {
                // Video started loading
              }}
            />
            </Box>
            {/* Video Controls Widget - Below video */}
            <VideoControlsWidget
              isPlaying={isVideoPlaying}
              onPlay={() => {
                if (videoPlayerRef.current) {
                  videoPlayerRef.current.play().catch((error: unknown) => {
                    console.debug(`[Segment ${segmentIndex}] Failed to play:`, error);
                  });
                }
              }}
              onPause={() => {
                if (videoPlayerRef.current) {
                  videoPlayerRef.current.pause();
                }
              }}
              onStop={() => {
                if (videoPlayerRef.current) {
                  videoPlayerRef.current.stop();
                }
              }}
              onInfoClick={() => {
                // Pause video and remember playing state
                if (videoPlayerRef.current) {
                  const videoElement = videoPlayerRef.current.getVideoElement();
                  if (videoElement) {
                    setWasPlayingBeforeModal(!videoElement.paused);
                    videoPlayerRef.current.pause();
                  }
                }
                setInfoModalOpen(true);
              }}
              timerange={timerange}
              segmentIndex={segmentIndex}
            />
          </Box>
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
      ref={cardRef}
      data-segment-index={segmentIndex}
      data-video-playing={isVideoPlaying ? 'true' : 'false'}
      data-video-completed={isVideoCompleted ? 'true' : 'false'}
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
    </Card>

    {/* Segment Info Modal */}
    <Dialog 
      open={infoModalOpen} 
      onClose={() => {
        setInfoModalOpen(false);
        // Resume video if it was playing before
        if (wasPlayingBeforeModal && videoPlayerRef.current) {
          videoPlayerRef.current.play().catch((error: unknown) => {
            console.debug(`[Segment ${segmentIndex}] Failed to resume video after closing modal:`, error);
          });
        }
      }} 
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

