import React, { useEffect, useRef, useImperativeHandle, useState, useCallback } from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import { Segment, Flow } from '../types';
import VideoTextOverlay from './VideoTextOverlay';
import VideoInfoButton from './VideoInfoButton';
import { API_BASE_URL } from '../services/api';

interface SegmentPlayerProps {
  segments: Segment[];
  flow: Flow | null;
  width?: number | string;
  height?: number | string;
  autoPlay?: boolean;
  onReady?: () => void;
  onError?: (error: unknown) => void;
  onEnded?: () => void;
  onInfoClick?: (segmentIndex: number) => void;
  onSegmentIndexChange?: (segmentIndex: number) => void;
}

const SegmentPlayer = React.forwardRef<any, SegmentPlayerProps>(({ 
  segments,
  flow,
  width = '100%', 
  height = 'auto',
  autoPlay = false,
  onReady,
  onError,
  onEnded,
  onInfoClick,
  onSegmentIndexChange
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentSegmentTimerange, setCurrentSegmentTimerange] = useState<string>('');
  const segmentUrlsRef = useRef<Map<number, string>>(new Map());
  const loadedSegmentsRef = useRef<Set<number>>(new Set());
  const preloadQueueRef = useRef<number[]>([]);
  const isPreloadingRef = useRef<boolean>(false);
  const isInitializedRef = useRef<boolean>(false);

  // Get proxy URL for segment
  const getProxyUrl = useCallback((segment: Segment, originalUrl: string): string => {
    if (!flow?.id || !segment.object_id) {
      return originalUrl;
    }
    
    const urlLower = originalUrl.toLowerCase();
    const isTS = urlLower.includes('.ts') || urlLower.endsWith('.ts') || 
                 urlLower.includes('transport') || urlLower.includes('mpegts') ||
                 (flow?.container && flow.container.toLowerCase().includes('mp2t'));
    
    if (isTS) {
      // API_BASE_URL already includes the full path: /api/tams/v8.0 (Docker) or http://docker1:8000/api/tams/v8.0 (local)
      let baseUrl = API_BASE_URL.replace(/\/$/, '');
      
      // Web Workers (used by mpegts.js) require absolute URLs
      // If baseUrl is relative (starts with /), convert it to absolute using window.location.origin
      if (typeof window !== 'undefined' && baseUrl.startsWith('/')) {
        baseUrl = `${window.location.origin}${baseUrl}`;
      }
      
      const encodedUrl = encodeURIComponent(originalUrl);
      let proxyUrl = `${baseUrl}/hls/flows/${flow.id}/segments/${segment.object_id}?url=${encodedUrl}`;
      
      if (typeof window !== 'undefined' && window.localStorage) {
        const token = localStorage.getItem('token');
        if (token) {
          proxyUrl += `&access_token=${encodeURIComponent(token)}`;
        }
      }
      
      // Debug logging to verify absolute URLs for Web Workers
      console.debug(`[SegmentPlayer] Proxy URL generated:`, {
        original: originalUrl.substring(0, 100),
        proxy: proxyUrl.substring(0, 150),
        baseUrl,
        isAbsolute: proxyUrl.startsWith('http'),
        willWorkInWorker: proxyUrl.startsWith('http')
      });
      
      return proxyUrl;
    }
    
    return originalUrl;
  }, [flow]);

  // Get URL for a segment
  const getSegmentUrl = useCallback((segment: Segment): string | null => {
    if (!segment.get_urls || segment.get_urls.length === 0) {
      return null;
    }
    
    const firstUrl = segment.get_urls[0];
    if (!firstUrl?.url) {
      return null;
    }
    
    return getProxyUrl(segment, firstUrl.url);
  }, [getProxyUrl]);

  // Load a specific segment
  const loadSegment = useCallback((index: number, url: string, wasPlaying: boolean = false) => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    
    console.debug(`[SegmentPlayer] Loading segment ${index}:`, url);
    
    // Clear old source
    video.src = '';
    video.load();
    
    // Set new source
    video.src = url;
    video.load();
    
    setCurrentSegmentIndex(index);
    const segment = segments[index];
    setCurrentSegmentTimerange(segment?.timerange?.value || '');
    
    if (onSegmentIndexChange) {
      onSegmentIndexChange(index);
    }

    const handleLoadedData = () => {
      console.debug(`[SegmentPlayer] Segment ${index} loaded`);
      if (wasPlaying) {
        video.play().catch((error) => {
          console.debug('Failed to play after segment load:', error);
        });
      }
    };

    const handleError = (e: Event) => {
      console.error(`[SegmentPlayer] Error loading segment ${index}:`, e);
      if (onError) {
        onError(e);
      }
    };

    video.addEventListener('loadeddata', handleLoadedData, { once: true });
    video.addEventListener('error', handleError, { once: true });
  }, [segments, onSegmentIndexChange, onError]);

  // Handle moving to next segment
  const handleNextSegment = useCallback(() => {
    const nextIndex = currentSegmentIndex + 1;
    
    if (nextIndex >= segments.length) {
      console.debug('[SegmentPlayer] All segments played');
      if (onEnded) onEnded();
      return;
    }

    const nextSegment = segments[nextIndex];
    const url = segmentUrlsRef.current.get(nextIndex);
    const video = videoRef.current;
    const wasPlaying = video ? !video.paused : false;
    
    if (!url) {
      console.warn(`[SegmentPlayer] URL not available for segment ${nextIndex}, trying to get it`);
      const fallbackUrl = getSegmentUrl(nextSegment);
      if (!fallbackUrl) {
        console.error(`[SegmentPlayer] Cannot get URL for segment ${nextIndex}`);
        if (onError) {
          onError(new Error(`Cannot get URL for segment ${nextIndex}`));
        }
        return;
      }
      segmentUrlsRef.current.set(nextIndex, fallbackUrl);
      loadSegment(nextIndex, fallbackUrl, wasPlaying);
    } else {
      loadSegment(nextIndex, url, wasPlaying);
    }
  }, [currentSegmentIndex, segments, getSegmentUrl, onEnded, onError, loadSegment]);

  // Load first segment immediately
  useEffect(() => {
    if (segments.length === 0 || !videoRef.current || isInitializedRef.current) {
      if (!isInitializedRef.current) {
        console.debug('[SegmentPlayer] Waiting for segments or video element', { 
          segmentsLength: segments.length, 
          hasVideo: !!videoRef.current 
        });
      }
      return;
    }

    const firstSegment = segments[0];
    
    // Check if segment has URLs
    if (!firstSegment.get_urls || firstSegment.get_urls.length === 0) {
      console.warn('[SegmentPlayer] First segment has no get_urls, segments may not be loaded yet');
      return;
    }
    
    const url = getSegmentUrl(firstSegment);
    
    if (!url) {
      console.error('[SegmentPlayer] No URL available for first segment', firstSegment);
      if (onError) {
        onError(new Error('No URL available for first segment'));
      }
      return;
    }

    console.debug('[SegmentPlayer] Loading first segment:', url);
    const video = videoRef.current;
    isInitializedRef.current = true;
    
    // Clear any existing source
    video.src = '';
    video.load();
    
    // Set new source
    video.src = url;
    video.load();
    
    segmentUrlsRef.current.set(0, url);
    setCurrentSegmentIndex(0);
    setCurrentSegmentTimerange(firstSegment.timerange?.value || '');
    
    const handleLoadedMetadata = () => {
      console.debug('[SegmentPlayer] First segment metadata loaded');
      if (onReady) onReady();
    };

    const handleLoadedData = () => {
      console.debug('[SegmentPlayer] First segment data loaded, ready to play');
      if (autoPlay) {
        video.play().catch((error) => {
          console.debug('Autoplay prevented:', error);
        });
      }
    };

    const handleCanPlay = () => {
      console.debug('[SegmentPlayer] First segment can play');
      if (autoPlay && video.paused) {
        video.play().catch((error) => {
          console.debug('Autoplay prevented:', error);
        });
      }
    };

    const handleError = (e: Event) => {
      console.error('[SegmentPlayer] Error loading first segment:', e, video.error);
      if (onError) {
        onError(e);
      }
    };

    const handleEnded = () => {
      console.debug('[SegmentPlayer] First segment ended, moving to next');
      const nextIndex = 1;
      if (nextIndex >= segments.length) {
        console.debug('[SegmentPlayer] All segments played');
        if (onEnded) onEnded();
        return;
      }

      const nextSegment = segments[nextIndex];
      const nextUrl = segmentUrlsRef.current.get(nextIndex);
      const stillPlaying = !video.paused;
      
      if (!nextUrl) {
        console.warn(`[SegmentPlayer] URL not available for segment ${nextIndex}, trying to get it`);
        const fallbackUrl = getSegmentUrl(nextSegment);
        if (!fallbackUrl) {
          console.error(`[SegmentPlayer] Cannot get URL for segment ${nextIndex}`);
          if (onError) {
            onError(new Error(`Cannot get URL for segment ${nextIndex}`));
          }
          return;
        }
        segmentUrlsRef.current.set(nextIndex, fallbackUrl);
        loadSegment(nextIndex, fallbackUrl, stillPlaying);
      } else {
        loadSegment(nextIndex, nextUrl, stillPlaying);
      }
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
    video.addEventListener('loadeddata', handleLoadedData, { once: true });
    video.addEventListener('canplay', handleCanPlay, { once: true });
    video.addEventListener('error', handleError, { once: true });
    video.addEventListener('ended', handleEnded, { once: true });

    return () => {
      // Cleanup is handled by { once: true }
    };
  }, [segments, getSegmentUrl, autoPlay, onReady, onError, loadSegment, onEnded]);

  // Preload segments in background
  const preloadSegment = useCallback(async (index: number) => {
    if (index >= segments.length || loadedSegmentsRef.current.has(index)) {
      return;
    }

    const segment = segments[index];
    const url = getSegmentUrl(segment);
    
    if (!url) {
      console.warn(`[SegmentPlayer] No URL for segment ${index}`);
      return;
    }

    console.debug(`[SegmentPlayer] Preloading segment ${index}:`, url);
    
    // Preload by creating a video element and loading it
    const preloadVideo = document.createElement('video');
    preloadVideo.preload = 'auto';
    preloadVideo.src = url;
    
    return new Promise<void>((resolve) => {
      const handleCanPlay = () => {
        console.debug(`[SegmentPlayer] Segment ${index} preloaded`);
        loadedSegmentsRef.current.add(index);
        segmentUrlsRef.current.set(index, url);
        preloadVideo.removeEventListener('canplay', handleCanPlay);
        preloadVideo.removeEventListener('error', handleError);
        resolve();
      };

      const handleError = () => {
        console.warn(`[SegmentPlayer] Error preloading segment ${index}`);
        preloadVideo.removeEventListener('canplay', handleCanPlay);
        preloadVideo.removeEventListener('error', handleError);
        resolve();
      };

      preloadVideo.addEventListener('canplay', handleCanPlay);
      preloadVideo.addEventListener('error', handleError);
      
      // Start loading
      preloadVideo.load();
    });
  }, [segments, getSegmentUrl]);

  // Background preloading process
  useEffect(() => {
    if (segments.length === 0 || isPreloadingRef.current || !isInitializedRef.current) return;

    const startPreloading = async () => {
      isPreloadingRef.current = true;
      
      // Preload segments starting from index 1 (0 is already loaded)
      for (let i = 1; i < segments.length; i++) {
        if (!loadedSegmentsRef.current.has(i)) {
          await preloadSegment(i);
          // Small delay between preloads to avoid overwhelming the browser
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      isPreloadingRef.current = false;
    };

    // Start preloading after a short delay to let first segment start
    const timeout = setTimeout(() => {
      startPreloading();
    }, 500);

    return () => {
      clearTimeout(timeout);
    };
  }, [segments, preloadSegment]);


  // Handle next clip button
  const handleNextClip = () => {
    handleNextSegment();
  };

  // Handle previous clip button
  const handlePreviousClip = () => {
    const prevIndex = currentSegmentIndex - 1;
    
    if (prevIndex < 0) {
      // Already at first segment, seek to start
      if (videoRef.current) {
        videoRef.current.currentTime = 0;
      }
      return;
    }

    const url = segmentUrlsRef.current.get(prevIndex);
    const video = videoRef.current;
    const wasPlaying = video ? !video.paused : false;
    
    if (url) {
      loadSegment(prevIndex, url, wasPlaying);
    } else {
      const segment = segments[prevIndex];
      const fallbackUrl = getSegmentUrl(segment);
      if (fallbackUrl) {
        segmentUrlsRef.current.set(prevIndex, fallbackUrl);
        loadSegment(prevIndex, fallbackUrl, wasPlaying);
      }
    }
  };

  // Handle play/pause
  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;
    
    if (video.paused) {
      video.play().catch((error) => {
        console.debug('Failed to play:', error);
      });
    } else {
      video.pause();
    }
  };

  // Handle stop
  const handleStop = () => {
    const video = videoRef.current;
    if (!video) return;
    
    video.pause();
    video.currentTime = 0;
  };

  // Track playing state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, []);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    play: () => {
      if (videoRef.current) {
        return videoRef.current.play();
      }
      return Promise.resolve();
    },
    pause: () => {
      if (videoRef.current) {
        videoRef.current.pause();
      }
    },
    getVideoElement: () => videoRef.current,
    seekToNextClip: handleNextClip
  }));

  const canGoToNext = currentSegmentIndex < segments.length - 1;
  const canGoToPrevious = currentSegmentIndex > 0;

  return (
    <Box sx={{ 
      width: '100%', 
      position: 'relative',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    }}>
      <Box sx={{ 
        position: 'relative', 
        width: typeof width === 'string' ? width : `${width}px`,
        height: typeof height === 'string' ? height : `${height}px`,
        maxWidth: '100%',
        backgroundColor: '#000',
        borderRadius: 1,
        overflow: 'hidden',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      }}>
        <video
          ref={videoRef}
          controls
          playsInline
          loop={false}
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            objectFit: 'contain',
            backgroundColor: '#000',
          }}
          preload="auto"
          crossOrigin="anonymous"
        >
          Your browser does not support the video tag.
        </video>
        
        {/* Timerange Overlay - Top Right */}
        <VideoTextOverlay 
          text={currentSegmentTimerange || ''} 
          position="top-right"
        />
        
        {/* Info Button - Top Left */}
        {onInfoClick && segments.length > 0 && currentSegmentIndex >= 0 && (
          <VideoInfoButton 
            onClick={() => onInfoClick(currentSegmentIndex)}
            position="top-left"
            tooltip="Segment Info"
          />
        )}
        
        {/* Compact Controls - Bottom Center */}
        {segments.length > 0 && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 8,
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 1000,
              display: 'flex',
              gap: 0.5,
              alignItems: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.75)',
              padding: '4px 8px',
              borderRadius: 1,
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
            }}
          >
            <Tooltip title="Previous Clip">
              <span>
                <IconButton
                  onClick={handlePreviousClip}
                  disabled={!canGoToPrevious}
                  size="small"
                  sx={{
                    color: '#fff',
                    padding: '4px',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    },
                    '&.Mui-disabled': {
                      color: 'rgba(255, 255, 255, 0.3)',
                    },
                  }}
                >
                  <SkipPreviousIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            
            <Tooltip title={isPlaying ? "Pause" : "Play"}>
              <IconButton
                onClick={handlePlayPause}
                size="small"
                sx={{
                  color: '#fff',
                  backgroundColor: 'rgba(255, 255, 255, 0.15)',
                  padding: '4px',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.25)',
                  },
                }}
              >
                {isPlaying ? <PauseIcon fontSize="small" /> : <PlayArrowIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Stop">
              <IconButton
                onClick={handleStop}
                size="small"
                sx={{
                  color: '#fff',
                  padding: '4px',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                  },
                }}
              >
                <StopIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Next Clip">
              <span>
                <IconButton
                  onClick={handleNextClip}
                  disabled={!canGoToNext}
                  size="small"
                  sx={{
                    color: '#fff',
                    padding: '4px',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    },
                    '&.Mui-disabled': {
                      color: 'rgba(255, 255, 255, 0.3)',
                    },
                  }}
                >
                  <SkipNextIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Box>
        )}
      </Box>
    </Box>
  );
});

SegmentPlayer.displayName = 'SegmentPlayer';

export default SegmentPlayer;

