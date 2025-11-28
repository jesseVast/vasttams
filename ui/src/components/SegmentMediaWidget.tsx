import React, { useRef, useEffect, useState, memo } from 'react';
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
import { API_BASE_URL, objectService } from '../services/api';

interface SegmentMediaWidgetProps {
  segment: Segment;
  flow?: Flow | null;
  width?: number | string;
  height?: number | string;
  isFirst?: boolean; // Flag to indicate if this is the first video (load immediately)
  videoPlayerType?: VideoPlayerType; // Which video player to use: 'videojs', 'react-player', or 'native'
  autoPlayEnabled?: boolean;
  segmentIndex?: number;
  loadImmediately?: boolean; // Force immediate loading (bypasses IntersectionObserver)
  useHLS?: boolean; // Use HLS playlist instead of individual segment
  hlsManifestUrl?: string | null; // HLS manifest blob URL (shared across all players)
  hlsStartTime?: number; // Time offset in seconds to start playback
  hlsSegmentDuration?: number; // Segment duration in seconds (to stop playback at end)
  hlsSegmentUrl?: string; // Direct segment URL from parsed M3U8 manifest (preferred over manifest)
}

type MediaType = 'video' | 'image' | 'audio' | 'data' | 'unknown';

// Component to monitor HLS playback and stop at segment end
interface HLSPlaybackMonitorProps {
  videoPlayerRef: React.RefObject<any>;
  startTime: number;
  duration: number;
  segmentIndex?: number;
}

const HLSPlaybackMonitor: React.FC<HLSPlaybackMonitorProps> = ({
  videoPlayerRef,
  startTime,
  duration,
  segmentIndex,
}) => {
  useEffect(() => {
    const video = videoPlayerRef.current?.getVideoElement?.();
    if (!video) return;

    const endTime = startTime + duration;
    let checkInterval: NodeJS.Timeout | null = null;
    let lastCheckTime = 0;
    const checkThrottle = 200; // Only check every 200ms to reduce overhead
    let hasReachedEnd = false; // Track if we've already paused at the end

    const checkPlayback = () => {
      if (!video || video.paused) return;
      
      const now = Date.now();
      // Throttle checks to reduce overhead
      if (now - lastCheckTime < checkThrottle) return;
      lastCheckTime = now;
      
      // Check if we've reached or passed the segment end time
      if (!hasReachedEnd && video.currentTime >= endTime - 0.1) { // 0.1s tolerance
        hasReachedEnd = true;
        console.debug(`[Segment ${segmentIndex}] Reached segment end (${endTime}s), pausing playback`);
        video.pause();
        // Seek back to start of segment
        video.currentTime = startTime;
      } else if (hasReachedEnd && video.currentTime < endTime - 0.5) {
        // Reset flag if video has been seeked back significantly
        hasReachedEnd = false;
      }
    };

    // Only check when video is playing - use a longer interval to reduce overhead
    checkInterval = setInterval(() => {
      if (video && !video.paused) {
        checkPlayback();
      }
    }, 300); // Check every 300ms instead of 100ms

    // Listen to timeupdate events but throttle them
    let lastTimeUpdate = 0;
    const handleTimeUpdate = () => {
      const now = Date.now();
      if (now - lastTimeUpdate >= checkThrottle) {
        lastTimeUpdate = now;
        checkPlayback();
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    
    // Reset flag when video starts playing
    const handlePlay = () => {
      hasReachedEnd = false;
    };
    video.addEventListener('play', handlePlay);

    return () => {
      if (checkInterval) {
        clearInterval(checkInterval);
      }
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
    };
  }, [videoPlayerRef, startTime, duration, segmentIndex]);

  return null; // This component doesn't render anything
};

const SegmentMediaWidget: React.FC<SegmentMediaWidgetProps> = ({ 
  segment, 
  flow,
  width = 240, 
  height = 135,
  isFirst = false,
  videoPlayerType = 'native', // Default to native HTML5 for best performance
  autoPlayEnabled = false,
  segmentIndex,
  loadImmediately = false, // Force immediate loading (bypasses IntersectionObserver)
  useHLS = false, // Use HLS playlist instead of individual segment
  hlsManifestUrl = null, // HLS manifest blob URL (shared across all players)
  hlsStartTime = 0, // Time offset in seconds to start playback
  hlsSegmentDuration = undefined, // Segment duration in seconds (to stop playback at end)
  hlsSegmentUrl = undefined // Direct segment URL from parsed M3U8 manifest (preferred over manifest)
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const videoPlayerRef = useRef<any>(null);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [isInViewport, setIsInViewport] = useState(isFirst || loadImmediately); // First video or forced load
  const [intersectionRatio, setIntersectionRatio] = useState(0); // Track how much is visible
  const [wasPlayingBeforeModal, setWasPlayingBeforeModal] = useState<boolean>(false);
  const [shouldLoadVideo, setShouldLoadVideo] = useState(isFirst || loadImmediately); // Track if video should be loaded
  const [shouldUnloadVideo, setShouldUnloadVideo] = useState(false); // Track if video should be unloaded
  const [retryWithMpegts, setRetryWithMpegts] = useState(false); // Track if we should retry with mpegts.js after native player error
  const [isVideoPlaying, setIsVideoPlaying] = useState(false); // Track if video is actually playing
  const [isVideoCompleted, setIsVideoCompleted] = useState(false); // Track if video has completed
  const [objectData, setObjectData] = useState<any>(null); // Store object data for tags
  const [loadingObject, setLoadingObject] = useState(false); // Track object loading state
  
  // Fetch object data when modal opens to get tags
  useEffect(() => {
    if (infoModalOpen && segment.object_id && !objectData && !loadingObject) {
      setLoadingObject(true);
      objectService.get(segment.object_id)
        .then((obj) => {
          setObjectData(obj);
          setLoadingObject(false);
        })
        .catch((error) => {
          console.error('Failed to fetch object data:', error);
          setLoadingObject(false);
        });
    }
  }, [infoModalOpen, segment.object_id, objectData, loadingObject]);
  
  // Format object for display (similar to DetailModal)
  const formatObject = (obj: any, depth = 0): React.ReactNode => {
    if (obj === null || obj === undefined) return '-';
    if (typeof obj === 'string') return obj;
    if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj);
    if (Array.isArray(obj)) {
      if (obj.length === 0) return '-';
      return (
        <Box>
          {obj.map((item, idx) => (
            <Box key={idx} sx={{ mb: 0.5 }}>
              {formatObject(item, depth + 1)}
            </Box>
          ))}
        </Box>
      );
    }
    if (typeof obj === 'object') {
      return (
        <Box sx={{ pl: depth > 0 ? 2 : 0 }}>
          {Object.entries(obj).map(([key, value]) => (
            <Box key={key} sx={{ mb: 0.5 }}>
              <Typography variant="body2" component="span" sx={{ fontWeight: 'bold' }}>
                {key}:
              </Typography>{' '}
              <Typography variant="body2" component="span">
                {formatObject(value, depth + 1)}
              </Typography>
            </Box>
          ))}
        </Box>
      );
    }
    return String(obj);
  };
  
  const getFirstPresignedUrl = (seg: Segment) => {
    return seg.get_urls?.find(url => url.presigned && url.url) || seg.get_urls?.[0];
  };

  // Convert URLs to proxy URLs for CORS support (especially needed for mpegts.js)
  const getProxyUrl = (originalUrl: string): string => {
    if (!flow?.id || !segment.object_id) {
      console.warn('[SegmentMediaWidget] Cannot create proxy URL: missing flow.id or segment.object_id');
      return originalUrl;
    }
    
    // API_BASE_URL already includes the full path: /api/tams/v8.0 (Docker) or http://docker1:8000/api/tams/v8.0 (local)
    let baseUrl = API_BASE_URL.replace(/\/$/, '');
    
    // Web Workers (used by mpegts.js) require absolute URLs
    // If baseUrl is relative (starts with /), convert it to absolute using window.location.origin
    if (typeof window !== 'undefined' && baseUrl.startsWith('/')) {
      baseUrl = `${window.location.origin}${baseUrl}`;
    }
    
    const encodedUrl = encodeURIComponent(originalUrl);
    
    // Include token in query parameter for authentication (like HLS playlists)
    let proxyUrl = `${baseUrl}/hls/flows/${flow.id}/segments/${segment.object_id}?url=${encodedUrl}`;
    
    if (typeof window !== 'undefined' && window.localStorage) {
      const token = localStorage.getItem('token');
      if (token) {
        proxyUrl += `&access_token=${encodeURIComponent(token)}`;
      }
    }
    
    console.debug(`[Segment ${segmentIndex}] Proxying URL:`, {
      original: originalUrl.substring(0, 100),
      proxy: proxyUrl.substring(0, 150),
      baseUrl,
      isAbsolute: proxyUrl.startsWith('http')
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
  // Skip IntersectionObserver in multiview mode (loadImmediately=true) to prevent flickering
  useEffect(() => {
    if (!cardRef.current || mediaType !== 'video') return;
    
    // If loadImmediately is true, skip IntersectionObserver and load immediately
    // In multiview, all videos are loaded but autoplay logic is disabled
    if (loadImmediately) {
      setShouldLoadVideo(true);
      setIsInViewport(true);
      setIntersectionRatio(1);
      // Don't set up IntersectionObserver in multiview - videos are controlled manually
      return;
    }

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mediaType, segmentIndex, shouldLoadVideo]);

  // Handle scroll-based playback: play only when highly visible, pause otherwise
  // Skip this logic in multiview mode (loadImmediately=true) to prevent flickering
  useEffect(() => {
    if (mediaType !== 'video' || !shouldLoadVideo || shouldUnloadVideo || loadImmediately) return;
    
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPlayEnabled, isInViewport, intersectionRatio, mediaType, segmentIndex, shouldLoadVideo, shouldUnloadVideo]);

  // Periodically sync video playing state with actual video element state
  // This is important for mpegts videos which might show first frame but not actually play
  // Also detects when video ends by checking currentTime vs duration
  // Skip in multiview mode (loadImmediately=true) to prevent unnecessary state updates that cause flickering
  useEffect(() => {
    if (mediaType !== 'video' || !shouldLoadVideo || shouldUnloadVideo || loadImmediately) return;
    
    const syncInterval = setInterval(() => {
      if (videoPlayerRef.current) {
        const videoElement = videoPlayerRef.current.getVideoElement?.();
        if (videoElement) {
          const actuallyPlaying = !videoElement.paused && videoElement.readyState >= 2;
          const hasDuration = Boolean(videoElement.duration && !isNaN(videoElement.duration) && isFinite(videoElement.duration));
          const isAtEnd = hasDuration && videoElement.currentTime >= videoElement.duration - 0.1; // Within 0.1s of end
          const actuallyCompleted = isAtEnd || videoElement.ended;
          
          // Sync playing state
          if (actuallyPlaying !== isVideoPlaying) {
            console.debug(`[Segment ${segmentIndex}] Syncing playing state: ${isVideoPlaying} -> ${actuallyPlaying} (paused: ${videoElement.paused}, readyState: ${videoElement.readyState})`);
            setIsVideoPlaying(actuallyPlaying);
          }
          
          // Sync completed state - check if video has ended
          if (actuallyCompleted && !isVideoCompleted) {
            console.debug(`[Segment ${segmentIndex}] Video detected as completed (currentTime: ${videoElement.currentTime}, duration: ${videoElement.duration}, ended: ${videoElement.ended})`);
            setIsVideoCompleted(true);
            setIsVideoPlaying(false);
          } else if (!actuallyCompleted && isVideoCompleted && actuallyPlaying) {
            // Video restarted or resumed
            console.debug(`[Segment ${segmentIndex}] Video resumed after completion`);
            setIsVideoCompleted(false);
          }
        }
      }
    }, 200); // Check more frequently (every 200ms) for better responsiveness
    
    return () => clearInterval(syncInterval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mediaType, shouldLoadVideo, shouldUnloadVideo, segmentIndex, isVideoPlaying, isVideoCompleted]);

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
        // If direct segment URL is available (from parsed M3U8), use it directly with mpegts.js
        if (hlsSegmentUrl) {
          return (
            <Box sx={{ width: '100%' }}>
              <Box sx={{ position: 'relative', width: '100%', height: height, backgroundColor: '#000' }}>
                <VideoPlayer
                  ref={videoPlayerRef}
                  src={hlsSegmentUrl}
                  width="100%"
                  height={height}
                  controls
                  muted
                  playsInline
                  preload="metadata"
                  playerType="mpegts" // Use mpegts.js for individual .ts files
                  onReady={() => {
                  console.log(`[Segment ${segmentIndex}] ========== onReady CALLED (mpegts.js) ==========`, {
                    autoPlayEnabled,
                    isVideoCompleted,
                    hasPlayerRef: !!videoPlayerRef.current
                  });
                  
                  // Ensure player is ready for manual play even when autoplay is off
                  // The player needs to load metadata and buffer to be ready for manual playback
                  if (videoPlayerRef.current && !isVideoCompleted) {
                    const video = videoPlayerRef.current.getVideoElement?.();
                    if (video && !video.ended) {
                      console.log(`[Segment ${segmentIndex}] Video element state in onReady:`, {
                        paused: video.paused,
                        ended: video.ended,
                        readyState: video.readyState,
                        currentTime: video.currentTime,
                        duration: video.duration,
                        hasBuffer: video.buffered.length > 0,
                        bufferInfo: video.buffered.length > 0 
                          ? `${video.buffered.start(0)}-${video.buffered.end(video.buffered.length - 1)}`
                          : 'none'
                      });
                      
                      // For mpegts.js, the player starts loading when load() is called
                      // But we need to ensure it has enough data buffered for manual play
                      // Wait for video to be ready and have buffer
                      const ensureReady = () => {
                        // Don't do anything if video has ended
                        if (video.ended || isVideoCompleted) {
                          console.log(`[Segment ${segmentIndex}] Video has ended, skipping ready check`);
                          return;
                        }
                        
                        // Check if video has loaded enough data
                        // For mpegts, readyState >= 2 means we have metadata, >= 3 means we have some data
                        const isReady = video.readyState >= 2;
                        const hasBuffer = video.buffered.length > 0;
                        
                        console.log(`[Segment ${segmentIndex}] ensureReady check:`, {
                          readyState: video.readyState,
                          isReady,
                          hasBuffer,
                          paused: video.paused,
                          ended: video.ended,
                          autoPlayEnabled
                        });
                        
                        if (isReady) {
                          console.log(`[Segment ${segmentIndex}] mpegts player ready for playback (autoplay: ${autoPlayEnabled}, readyState: ${video.readyState}, hasBuffer: ${hasBuffer})`);
                          
                          // Only start playback if autoplay is enabled
                          if (autoPlayEnabled && video.paused && !video.ended) {
                            // Wait for buffer if not ready yet
                            if (hasBuffer || video.readyState >= 3) {
                              console.log(`[Segment ${segmentIndex}] Starting autoplay...`);
                              video.play().then(() => {
                                console.log(`[Segment ${segmentIndex}] Direct segment autoplay started successfully`);
                              }).catch((error: unknown) => {
                                console.error(`[Segment ${segmentIndex}] Direct segment autoplay prevented:`, error);
                              });
                            } else {
                              console.log(`[Segment ${segmentIndex}] Waiting for buffer before autoplay...`);
                              // Wait a bit more for buffer
                              setTimeout(ensureReady, 100);
                            }
                          } else {
                            console.log(`[Segment ${segmentIndex}] Autoplay disabled - player ready for manual play`);
                          }
                          // When autoplay is off, the player is ready for manual play
                          // The play() method will handle waiting for sufficient buffer
                        } else if (video.readyState < 2 && !video.ended) {
                          console.log(`[Segment ${segmentIndex}] Video not ready yet (readyState: ${video.readyState}), waiting...`);
                          // Keep waiting for player to be ready
                          setTimeout(ensureReady, 100);
                        }
                      };
                      // Wait a bit for mpegts.js to load initial data
                      setTimeout(ensureReady, 300);
                    } else {
                      console.warn(`[Segment ${segmentIndex}] No video element or video ended in onReady`);
                    }
                  } else {
                    console.warn(`[Segment ${segmentIndex}] No player ref or video completed in onReady`);
                  }
                }}
                onPlay={() => {
                  // Update state when video starts playing
                  setIsVideoPlaying(true);
                  setIsVideoCompleted(false);
                  console.debug(`[Segment ${segmentIndex}] Direct segment video playing`);
                }}
                onEnded={() => {
                  // Only update state if it actually changed to prevent flickering
                  if (isVideoPlaying || !isVideoCompleted) {
                    setIsVideoPlaying(false);
                    setIsVideoCompleted(true);
                    console.debug(`[Segment ${segmentIndex}] Direct segment video completed`);
                  }
                  // Ensure video stays paused and doesn't restart
                  if (videoPlayerRef.current) {
                    const video = videoPlayerRef.current.getVideoElement?.();
                    if (video && !video.paused) {
                      video.pause();
                    }
                  }
                }}
                onError={(error) => {
                  console.error(`[Segment ${segmentIndex}] Direct segment playback error:`, error);
                }}
              />
              </Box>
              <VideoControlsWidget
                isPlaying={isVideoPlaying}
                onPlay={() => {
                  console.log(`[Segment ${segmentIndex}] ========== MANUAL PLAY BUTTON CLICKED ==========`);
                  if (videoPlayerRef.current) {
                    const videoElement = videoPlayerRef.current?.getVideoElement?.();
                    console.log(`[Segment ${segmentIndex}] Before play() call:`, {
                      hasPlayerRef: !!videoPlayerRef.current,
                      hasVideoElement: !!videoElement,
                      videoPaused: videoElement?.paused,
                      videoEnded: videoElement?.ended,
                      videoReadyState: videoElement?.readyState,
                      videoCurrentTime: videoElement?.currentTime,
                      videoDuration: videoElement?.duration,
                      hasBuffer: videoElement?.buffered.length > 0,
                      bufferInfo: videoElement?.buffered.length > 0 
                        ? `${videoElement.buffered.start(0)}-${videoElement.buffered.end(videoElement.buffered.length - 1)}`
                        : 'none',
                      autoPlayEnabled,
                      isVideoPlaying,
                      isVideoCompleted
                    });
                    
                    // Optimistically update state for immediate UI feedback
                    setIsVideoPlaying(true);
                    setIsVideoCompleted(false);
                    
                    const playPromise = videoPlayerRef.current.play();
                    console.log(`[Segment ${segmentIndex}] play() called, promise:`, playPromise);
                    
                    playPromise
                      .then(() => {
                        // State already updated, but verify
                        console.log(`[Segment ${segmentIndex}] ========== Manual play() promise RESOLVED ==========`);
                        // Check if video is actually playing
                        const videoElementAfter = videoPlayerRef.current?.getVideoElement?.();
                        if (videoElementAfter) {
                          console.log(`[Segment ${segmentIndex}] Video state after play() resolved:`, {
                            paused: videoElementAfter.paused,
                            ended: videoElementAfter.ended,
                            readyState: videoElementAfter.readyState,
                            currentTime: videoElementAfter.currentTime,
                            duration: videoElementAfter.duration,
                            hasBuffer: videoElementAfter.buffered.length > 0
                          });
                        }
                      })
                      .catch((error: unknown) => {
                        // Revert state on error
                        setIsVideoPlaying(false);
                        console.error(`[Segment ${segmentIndex}] ========== Manual play() promise REJECTED ==========`, error);
                        const videoElementAfter = videoPlayerRef.current?.getVideoElement?.();
                        if (videoElementAfter) {
                          console.error(`[Segment ${segmentIndex}] Video state after play() rejected:`, {
                            paused: videoElementAfter.paused,
                            ended: videoElementAfter.ended,
                            readyState: videoElementAfter.readyState,
                            currentTime: videoElementAfter.currentTime,
                            duration: videoElementAfter.duration,
                            error: videoElementAfter.error
                          });
                        }
                      });
                  } else {
                    console.error(`[Segment ${segmentIndex}] videoPlayerRef.current is null - cannot play`);
                  }
                }}
                onPause={() => {
                  if (videoPlayerRef.current) {
                    videoPlayerRef.current.pause();
                    // Immediately update state for responsive UI
                    setIsVideoPlaying(false);
                  }
                }}
                onStop={() => {
                  if (videoPlayerRef.current) {
                    videoPlayerRef.current.stop();
                    setIsVideoPlaying(false);
                    setIsVideoCompleted(false);
                  }
                }}
                onInfoClick={() => {
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
        }
        
        // If HLS mode and manifest URL available, use HLS player with time offset (fallback)
        if (useHLS && hlsManifestUrl) {
          return (
            <Box sx={{ width: '100%' }}>
              <Box sx={{ position: 'relative', width: '100%', height: height, backgroundColor: '#000' }}>
                <VideoPlayer
                ref={videoPlayerRef}
                src={hlsManifestUrl}
                width="100%"
                height={height}
                controls
                muted
                playsInline
                preload="metadata" // Use metadata instead of auto to avoid auto-play
                playerType="hls"
                onReady={() => {
                  // Seek to the correct time offset when ready
                  // Wait for hls.js to fully initialize and load segments before seeking
                  if (videoPlayerRef.current && hlsStartTime !== undefined && hlsStartTime > 0) {
                    const video = videoPlayerRef.current.getVideoElement?.();
                    const hlsPlayer = videoPlayerRef.current?.getHlsPlayer?.();
                    if (video && hlsPlayer) {
                      // Wait for video to have duration and hls.js to be ready
                      // Seek BEFORE any playback starts to avoid interruption
                      let retryCount = 0;
                      const maxRetries = 100; // 10 seconds max wait
                      const seekToTime = () => {
                        retryCount++;
                        // Check if video is ready and duration is available
                        const isReady = video.readyState >= 2 && video.duration > 0 && video.duration > hlsStartTime;
                        // Check if hls.js has loaded at least one level
                        const hlsReady = hlsPlayer.levels && hlsPlayer.levels.length > 0;
                        
                        if (isReady && hlsReady) {
                          // Store whether video was playing before seeking
                          const wasPlaying = !video.paused;
                          
                          // Ensure video is paused before seeking
                          if (!video.paused) {
                            video.pause();
                          }
                          
                          // Seek to the start time
                          try {
                            video.currentTime = Math.min(hlsStartTime, video.duration);
                            console.debug(`[Segment ${segmentIndex}] HLS player seeked to ${hlsStartTime}s (duration: ${video.duration}, readyState: ${video.readyState})`);
                            
                            // After seeking, resume playback if autoplay is enabled or if it was playing before
                            if (autoPlayEnabled || wasPlaying) {
                              // Wait for seek to complete and buffer to be ready, then play
                              const attemptPlay = () => {
                                if (video.paused) {
                                  // Check if we have enough buffered data
                                  const hasBuffer = video.buffered.length > 0 && 
                                    video.buffered.end(video.buffered.length - 1) > video.currentTime + 0.5;
                                  const isReady = video.readyState >= 3;
                                  
                                  if (isReady && (hasBuffer || video.readyState >= 4)) {
                                    video.play().then(() => {
                                      console.debug(`[Segment ${segmentIndex}] HLS playback started after seek`);
                                    }).catch((error: unknown) => {
                                      console.debug(`[Segment ${segmentIndex}] Autoplay after seek prevented:`, error);
                                    });
                                  } else if (video.readyState < 4) {
                                    // Wait a bit more for buffer to fill
                                    setTimeout(attemptPlay, 100);
                                  }
                                }
                              };
                              // Start attempting to play after a short delay
                              setTimeout(attemptPlay, 300);
                            }
                          } catch (err) {
                            console.warn(`[Segment ${segmentIndex}] Seek failed:`, err);
                          }
                        } else if (retryCount < maxRetries) {
                          // Retry after a short delay
                          setTimeout(seekToTime, 100);
                        } else {
                          console.warn(`[Segment ${segmentIndex}] Failed to seek to ${hlsStartTime}s after ${maxRetries} retries (readyState: ${video.readyState}, duration: ${video.duration}, hlsReady: ${hlsReady})`);
                        }
                      };
                      // Start seeking after a delay to let hls.js initialize
                      setTimeout(seekToTime, 300);
                    } else if (video && !hlsPlayer) {
                      // Fallback: try without hls.js player reference
                      console.warn(`[Segment ${segmentIndex}] HLS player reference not available, using direct seek`);
                      const seekToTime = () => {
                        if (video.readyState >= 2 && video.duration > 0 && video.duration > hlsStartTime) {
                          const wasPlaying = !video.paused;
                          if (!video.paused) {
                            video.pause();
                          }
                          video.currentTime = Math.min(hlsStartTime, video.duration);
                          console.debug(`[Segment ${segmentIndex}] HLS player seeked to ${hlsStartTime}s (fallback method)`);
                          
                          // Resume playback if autoplay is enabled or if it was playing before
                          if (autoPlayEnabled || wasPlaying) {
                            const attemptPlay = () => {
                              if (video.paused) {
                                const hasBuffer = video.buffered.length > 0 && 
                                  video.buffered.end(video.buffered.length - 1) > video.currentTime + 0.5;
                                const isReady = video.readyState >= 3;
                                
                                if (isReady && (hasBuffer || video.readyState >= 4)) {
                                  video.play().then(() => {
                                    console.debug(`[Segment ${segmentIndex}] HLS playback started after seek (fallback)`);
                                  }).catch((error: unknown) => {
                                    console.debug(`[Segment ${segmentIndex}] Autoplay after seek prevented:`, error);
                                  });
                                } else if (video.readyState < 4) {
                                  setTimeout(attemptPlay, 100);
                                }
                              }
                            };
                            setTimeout(attemptPlay, 300);
                          }
                        } else {
                          setTimeout(seekToTime, 100);
                        }
                      };
                      setTimeout(seekToTime, 300);
                    }
                  } else if (videoPlayerRef.current && autoPlayEnabled) {
                    // If no start time offset, just start playback if autoplay is enabled
                    const video = videoPlayerRef.current.getVideoElement?.();
                    if (video) {
                      const attemptPlay = () => {
                        if (video.paused) {
                          const hasBuffer = video.buffered.length > 0 && 
                            video.buffered.end(video.buffered.length - 1) > video.currentTime + 0.5;
                          const isReady = video.readyState >= 3;
                          
                          if (isReady && (hasBuffer || video.readyState >= 4)) {
                            video.play().then(() => {
                              console.debug(`[Segment ${segmentIndex}] HLS playback started (no offset)`);
                            }).catch((error: unknown) => {
                              console.debug(`[Segment ${segmentIndex}] Autoplay prevented:`, error);
                            });
                          } else if (video.readyState < 4) {
                            setTimeout(attemptPlay, 100);
                          }
                        }
                      };
                      // Wait a bit for hls.js to load initial segments
                      setTimeout(attemptPlay, 500);
                    }
                  }
                }}
                onError={(error) => {
                  console.error(`[Segment ${segmentIndex}] HLS playback error:`, error);
                }}
              />
              {/* Monitor playback and stop at segment end for HLS */}
              {/* Only enable monitor in multiview mode (loadImmediately) or when autoplay is enabled */}
              {/* This prevents flickering in scrollview when autoplay is off */}
              {useHLS && hlsSegmentDuration !== undefined && hlsStartTime !== undefined && (loadImmediately || autoPlayEnabled) && (
                <HLSPlaybackMonitor
                  videoPlayerRef={videoPlayerRef}
                  startTime={hlsStartTime}
                  duration={hlsSegmentDuration}
                  segmentIndex={segmentIndex}
                />
              )}
              <VideoControlsWidget
                isPlaying={isVideoPlaying}
                onPlay={() => {
                  if (videoPlayerRef.current) {
                    // Optimistically update state for immediate UI feedback
                    setIsVideoPlaying(true);
                    setIsVideoCompleted(false);
                    videoPlayerRef.current.play()
                      .then(() => {
                        console.debug(`[Segment ${segmentIndex}] Manual play successful`);
                      })
                      .catch((error: unknown) => {
                        // Revert state on error
                        setIsVideoPlaying(false);
                        console.debug(`[Segment ${segmentIndex}] Failed to play:`, error);
                      });
                  }
                }}
                onPause={() => {
                  if (videoPlayerRef.current) {
                    videoPlayerRef.current.pause();
                    // Immediately update state for responsive UI
                    setIsVideoPlaying(false);
                  }
                }}
                onStop={() => {
                  if (videoPlayerRef.current) {
                    videoPlayerRef.current.stop();
                    setIsVideoPlaying(false);
                    setIsVideoCompleted(false);
                  }
                }}
                onInfoClick={() => {
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
            </Box>
          );
        }
        
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
                  // Video completed - only update state if it actually changed to prevent flashing
                  if (isVideoPlaying || !isVideoCompleted) {
                    setIsVideoPlaying(false);
                    setIsVideoCompleted(true);
                    console.debug(`[Segment ${segmentIndex}] Video completed`);
                  }
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
                  // Optimistically update state for immediate UI feedback
                  setIsVideoPlaying(true);
                  setIsVideoCompleted(false);
                  videoPlayerRef.current.play()
                    .then(() => {
                      console.debug(`[Segment ${segmentIndex}] Manual play successful`);
                    })
                    .catch((error: unknown) => {
                      // Revert state on error
                      setIsVideoPlaying(false);
                      console.debug(`[Segment ${segmentIndex}] Failed to play:`, error);
                    });
                }
              }}
              onPause={() => {
                if (videoPlayerRef.current) {
                  videoPlayerRef.current.pause();
                  // Immediately update state for responsive UI
                  setIsVideoPlaying(false);
                }
              }}
              onStop={() => {
                if (videoPlayerRef.current) {
                  videoPlayerRef.current.stop();
                  setIsVideoPlaying(false);
                  setIsVideoCompleted(false);
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

  // Check if width is "100%" to determine if we're in multiview mode
  const isMultiview = width === "100%" || width === "100%";
  
  return (
    <>
    <Card 
      ref={cardRef}
      data-segment-index={segmentIndex}
      data-video-playing={isVideoPlaying ? 'true' : 'false'}
      data-video-completed={isVideoCompleted ? 'true' : 'false'}
      sx={{ 
        width: isMultiview ? '100%' : width, 
        minWidth: isMultiview ? 0 : width,
        maxWidth: isMultiview ? '100%' : width,
        display: 'flex',
        flexDirection: 'column',
        margin: isMultiview ? 0 : 1, // No margin in multiview
        height: isMultiview ? '100%' : 'auto', // Full height in multiview
        overflow: 'hidden',
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

            {/* Tags from Object */}
            {(() => {
              // Handle tags that might be nested under 'root' or at top level
              const tags = objectData?.tags;
              if (!tags) return null;
              
              // Check if tags has a 'root' property with content
              const tagsToDisplay = tags.root && typeof tags.root === 'object' 
                ? tags.root 
                : tags;
              
              // Check if there are any actual tag key-value pairs
              const hasTags = tagsToDisplay && typeof tagsToDisplay === 'object' 
                && Object.keys(tagsToDisplay).length > 0;
              
              if (!hasTags) return null;
              
              return (
                <Paper sx={{ p: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                    Tags (from Object)
                  </Typography>
                  <Divider sx={{ mb: 1 }} />
                  <Box sx={{ mt: 0.5 }}>
                    {formatObject(tagsToDisplay)}
                  </Box>
                </Paper>
              );
            })()}

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

// Memoize component to prevent unnecessary re-renders when other videos play
// Only re-render if relevant props actually change
export default memo(SegmentMediaWidget, (prevProps, nextProps) => {
  // Return true if props are equal (skip re-render), false if different (re-render)
  const propsEqual = 
    prevProps.segment.object_id === nextProps.segment.object_id &&
    prevProps.flow?.id === nextProps.flow?.id &&
    prevProps.autoPlayEnabled === nextProps.autoPlayEnabled &&
    prevProps.loadImmediately === nextProps.loadImmediately &&
    prevProps.useHLS === nextProps.useHLS &&
    prevProps.hlsManifestUrl === nextProps.hlsManifestUrl &&
    prevProps.hlsSegmentUrl === nextProps.hlsSegmentUrl &&
    prevProps.hlsStartTime === nextProps.hlsStartTime &&
    prevProps.hlsSegmentDuration === nextProps.hlsSegmentDuration &&
    prevProps.segmentIndex === nextProps.segmentIndex &&
    prevProps.width === nextProps.width &&
    prevProps.height === nextProps.height;
  
  return propsEqual;
});

