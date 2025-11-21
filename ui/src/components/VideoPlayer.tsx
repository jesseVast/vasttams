import React, { useRef, useEffect, useState } from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
// Import CSS for video players (only loaded when used)
import 'video.js/dist/video-js.css';
import '@videojs/themes/dist/sea/index.css';

export type VideoPlayerType = 'videojs' | 'react-player' | 'native' | 'mpegts';

interface VideoPlayerProps {
  src: string;
  width?: number | string;
  height?: number | string;
  controls?: boolean;
  muted?: boolean;
  playsInline?: boolean;
  preload?: 'auto' | 'metadata' | 'none';
  playerType?: VideoPlayerType;
  onReady?: () => void;
  onError?: (error: unknown) => void; // More flexible error type
  onLoadStart?: () => void;
  onEnded?: () => void;
  light?: boolean; // For react-player light mode (thumbnail preview)
  playIcon?: React.ReactNode; // For react-player light mode
}

const VideoPlayer = React.forwardRef<any, VideoPlayerProps>(({
  src,
  width = '100%',
  height = '100%',
  controls = true,
  muted = false,
  playsInline = true,
  preload = 'metadata',
  playerType = 'native',
  onReady,
  onError,
  onLoadStart,
  onEnded,
  light = false,
  playIcon,
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Expose play/pause methods via ref
  React.useImperativeHandle(ref, () => ({
    play: () => {
      if (playerType === 'native' && videoRef.current) {
        return videoRef.current.play();
      } else if (playerType === 'videojs' && videojsRef.current) {
        return videojsRef.current.play();
      } else if (playerType === 'mpegts' && mpegtsPlayerRef.current) {
        return mpegtsPlayerRef.current.play();
      }
      return Promise.resolve();
    },
    pause: () => {
      if (playerType === 'native' && videoRef.current) {
        videoRef.current.pause();
      } else if (playerType === 'videojs' && videojsRef.current) {
        videojsRef.current.pause();
      } else if (playerType === 'mpegts' && mpegtsPlayerRef.current) {
        mpegtsPlayerRef.current.pause();
      }
    },
    getVideoElement: () => videoRef.current
  }));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);

  // Validate src prop
  const isValidSrc = src && src.trim().length > 0;

  // Lazy load other players only when needed
  const [ReactPlayerComponent, setReactPlayerComponent] = useState<React.ComponentType<any> | null>(null);
  const [VideoJS, setVideoJS] = useState<any>(null);
  const [MpegtsJS, setMpegtsJS] = useState<any>(null);
  const mpegtsPlayerRef = useRef<any>(null);

  // Clear loading state immediately if src is invalid
  useEffect(() => {
    if (!isValidSrc) {
      setLoading(false);
      setError('No video source provided');
    } else {
      setError(null);
    }
  }, [isValidSrc]);

  // Lazy load react-player
  useEffect(() => {
    if (playerType === 'react-player' && !ReactPlayerComponent) {
      import('react-player').then((module) => {
        setReactPlayerComponent(() => module.default);
      });
    }
  }, [playerType, ReactPlayerComponent]);

  // Lazy load video.js
  useEffect(() => {
    if (playerType === 'videojs' && !VideoJS) {
      import('video.js').then((videojsModule) => {
        setVideoJS(videojsModule.default);
      });
    }
  }, [playerType, VideoJS]);

  // Lazy load mpegts.js
  useEffect(() => {
    if (playerType === 'mpegts' && !MpegtsJS) {
      import('mpegts.js').then((mpegtsModule) => {
        setMpegtsJS(mpegtsModule.default);
      });
    }
  }, [playerType, MpegtsJS]);

  // Video.js player initialization
  const videojsRef = useRef<any>(null);
  const initTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Callback ref to initialize video.js when element is mounted
  const videoRefCallback = React.useCallback((element: HTMLVideoElement | null) => {
    // Cleanup any pending initialization
    if (initTimeoutRef.current) {
      clearTimeout(initTimeoutRef.current);
      initTimeoutRef.current = null;
    }
    
    // Handle cleanup when element is removed
    if (!element) {
      if (videojsRef.current) {
        try {
          videojsRef.current.dispose();
        } catch (err) {
          console.debug('Error disposing video.js player on unmount:', err);
        }
        videojsRef.current = null;
      }
      videoRef.current = null;
      return;
    }
    
    // Set ref for other player types
    videoRef.current = element;
    
    // Only initialize video.js if conditions are met
    if (playerType !== 'videojs' || !VideoJS || !isValidSrc) {
      return;
    }
    
    // Element is mounted, initialize video.js
    if (videojsRef.current) {
      // Already initialized, just update source if needed
      if (videojsRef.current.src() !== src) {
        videojsRef.current.src(src);
      }
      return;
    }
    
    // Small delay to ensure element is fully in DOM
    initTimeoutRef.current = setTimeout(() => {
      if (!element || videojsRef.current) return;
      
      // Double-check element is in DOM
      if (!element.parentElement || !document.body.contains(element)) {
        console.warn('Video element not in DOM, retrying...');
        initTimeoutRef.current = setTimeout(() => {
          videoRefCallback(element);
        }, 100);
        return;
      }
      
      try {
        // Determine MIME type for better compatibility
        let mimeType = '';
        const srcLower = src.toLowerCase();
        if (srcLower.includes('.ts') || srcLower.endsWith('.ts')) {
          mimeType = 'video/mp2t';
        } else if (srcLower.includes('.mp4') || srcLower.endsWith('.mp4')) {
          mimeType = 'video/mp4';
        } else if (srcLower.includes('.webm') || srcLower.endsWith('.webm')) {
          mimeType = 'video/webm';
        }
        
        // Final validation - element must be a valid HTMLVideoElement
        if (!(element instanceof HTMLVideoElement)) {
          console.error('Invalid element type for video.js:', element);
          setError('Invalid video element');
          setLoading(false);
          return;
        }
        
        // Verify element is still in DOM
        if (!element.parentElement || !document.body.contains(element)) {
          console.warn('Element not in DOM, cannot initialize video.js');
          return;
        }
        
        console.debug('Initializing video.js with element:', element, 'src:', src);
        const player = VideoJS(element, {
          controls,
          muted,
          preload,
          playsinline: playsInline,
          fluid: true,
          responsive: true,
          fill: true,
          sources: mimeType ? [{ src, type: mimeType }] : [{ src }],
        });

        videojsRef.current = player;

        player.ready(() => {
          setLoading(false);
          setError(null);
          if (onReady) onReady();
        });

        player.on('loadstart', () => {
          setLoading(true);
          setError(null);
          if (onLoadStart) onLoadStart();
        });

        player.on('error', () => {
          setLoading(false);
          const error = player.error();
          let errorMessage = 'Video.js error';
          if (error) {
            errorMessage = `Video.js error: ${error.message || 'Unknown error'}`;
          }
          setError(errorMessage);
          if (onError) {
            onError(new Error(errorMessage));
          }
        });
      } catch (err) {
        console.error('Failed to initialize video.js:', err);
        setError(`Failed to initialize video player: ${err instanceof Error ? err.message : 'Unknown error'}`);
        setLoading(false);
      }
    }, 100);
  }, [playerType, VideoJS, src, isValidSrc, controls, muted, preload, playsInline, onReady, onError, onLoadStart]);
  
  // Cleanup on unmount or when dependencies change
  useEffect(() => {
    return () => {
      if (initTimeoutRef.current) {
        clearTimeout(initTimeoutRef.current);
        initTimeoutRef.current = null;
      }
      if (videojsRef.current) {
        try {
          videojsRef.current.dispose();
        } catch (err) {
          console.debug('Error disposing video.js player:', err);
        }
        videojsRef.current = null;
      }
    };
  }, [playerType, VideoJS, src]);

  // Update Video.js source when src changes
  useEffect(() => {
    if (playerType === 'videojs' && videojsRef.current && isValidSrc) {
      videojsRef.current.src(src);
    }
  }, [src, isValidSrc, playerType]);

  // Check if native video is already loaded when component mounts or src changes
  useEffect(() => {
    if (playerType === 'native' && videoRef.current && isValidSrc) {
      const video = videoRef.current;
      setError(null); // Clear error when src changes

      // If video already has metadata loaded, clear loading immediately
      if (video.readyState >= 1) {
        setLoading(false);
        if (onReady) onReady();
      }

      // Fallback timeout to clear loading if events don't fire
      const timeoutId = setTimeout(() => {
        if (loading && video.readyState >= 1) {
          console.debug('[VideoPlayer] Loading timeout - clearing loading state, readyState:', video.readyState);
          setLoading(false);
          if (onReady) onReady();
        } else if (loading && video.readyState === 0) {
          // Video hasn't started loading - might be a network/CORS issue
          console.warn('[VideoPlayer] Video not loading after 5s, readyState:', video.readyState);
          setError('Video failed to load - check URL and network');
          setLoading(false);
        }
      }, 5000); // 5 second timeout

      return () => clearTimeout(timeoutId);
    } else if (playerType === 'native' && !isValidSrc) {
      setLoading(false);
      setError('No video source provided');
    }
  }, [playerType, src, isValidSrc, loading, onReady]);

  // Initialize mpegts.js player for .ts files
  useEffect(() => {
    if (playerType !== 'mpegts' || !MpegtsJS || !videoRef.current || !isValidSrc) {
      // Cleanup if switching away from mpegts
      if (mpegtsPlayerRef.current) {
        try {
          mpegtsPlayerRef.current.destroy();
        } catch (err) {
          console.debug('Error destroying mpegts player:', err);
        }
        mpegtsPlayerRef.current = null;
      }
      return;
    }

    const video = videoRef.current;
    
    // Cleanup existing player
    if (mpegtsPlayerRef.current) {
      try {
        mpegtsPlayerRef.current.destroy();
      } catch (err) {
        console.debug('Error destroying mpegts player:', err);
      }
      mpegtsPlayerRef.current = null;
    }
    
    // Check if mpegts.js is supported
    if (MpegtsJS.isSupported()) {
      console.debug('[VideoPlayer] Initializing mpegts.js player');
      setLoading(true);
      setError(null);
      if (onLoadStart) onLoadStart();

      try {
        const player = MpegtsJS.createPlayer({
          type: 'mpegts',
          url: src,
          isLive: false,
          cors: true,
          withCredentials: false, // Don't send credentials for CORS
        }, {
          enableWorker: true,
          enableStashBuffer: false,
          stashInitialSize: 128,
          autoCleanupSourceBuffer: true,
        });

        player.attachMediaElement(video);
        player.load();

        mpegtsPlayerRef.current = player;

        // Handle player events
        player.on(MpegtsJS.Events.ERROR, (errorType: string, errorDetail: any, errorInfo: any) => {
          console.error('[VideoPlayer] mpegts.js error:', {
            errorType,
            errorDetail,
            errorInfo,
            src: src.substring(0, 150),
            isProxyUrl: src.includes('/hls/flows/'),
          });
          setLoading(false);
          
          // Provide more helpful error messages
          let errorMessage = `mpegts.js error: ${errorType}`;
          if (errorDetail) {
            if (errorDetail.msg) {
              errorMessage += ` - ${errorDetail.msg}`;
            } else if (typeof errorDetail === 'string') {
              errorMessage += ` - ${errorDetail}`;
            } else {
              errorMessage += ` - ${JSON.stringify(errorDetail)}`;
            }
          }
          
          // Check if it's a network/CORS error
          if (errorType === 'NetworkError' || (errorDetail && errorDetail.msg && errorDetail.msg.includes('fetch'))) {
            errorMessage += ' (This may be a CORS issue. Ensure the video URL is proxied correctly.)';
          }
          
          setError(errorMessage);
          if (onError) {
            onError(new Error(errorMessage));
          }
        });

        // When video metadata is loaded
        const handleLoadedMetadata = () => {
          console.debug('[VideoPlayer] mpegts.js metadata loaded');
          setLoading(false);
          setError(null);
          if (onReady) onReady();
        };

        video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });

        // Cleanup on unmount
        return () => {
          video.removeEventListener('loadedmetadata', handleLoadedMetadata);
          if (mpegtsPlayerRef.current) {
            try {
              mpegtsPlayerRef.current.destroy();
            } catch (err) {
              console.debug('Error destroying mpegts player on cleanup:', err);
            }
            mpegtsPlayerRef.current = null;
          }
        };
      } catch (err) {
        console.error('[VideoPlayer] Failed to initialize mpegts.js:', err);
        setLoading(false);
        const errorMessage = `Failed to initialize mpegts.js: ${err instanceof Error ? err.message : 'Unknown error'}`;
        setError(errorMessage);
        if (onError) {
          onError(err);
        }
      }
    } else {
      console.warn('[VideoPlayer] mpegts.js is not supported in this browser');
      setLoading(false);
      setError('mpegts.js is not supported in this browser');
      if (onError) {
        onError(new Error('mpegts.js is not supported'));
      }
    }
  }, [playerType, MpegtsJS, src, isValidSrc, onReady, onError, onLoadStart]);

  // Sync playing state with video element
  useEffect(() => {
    if (!videoRef.current) return;
    
    const video = videoRef.current;
    
    const updatePlayingState = () => {
      setIsPlaying(!video.paused);
    };
    
    // Initial state
    updatePlayingState();
    
    // Listen to play/pause events
    video.addEventListener('play', updatePlayingState);
    video.addEventListener('pause', updatePlayingState);
    
    return () => {
      video.removeEventListener('play', updatePlayingState);
      video.removeEventListener('pause', updatePlayingState);
    };
  }, [playerType, src]);

  // Auto-hide overlay after delay when playing, show when paused
  useEffect(() => {
    if (isPlaying && showOverlay) {
      const timer = setTimeout(() => {
        setShowOverlay(false);
      }, 2000); // Hide after 2 seconds when playing
      return () => clearTimeout(timer);
    } else if (!isPlaying) {
      // Show overlay when paused
      setShowOverlay(true);
    }
  }, [isPlaying, showOverlay]);

  // Native HTML5 video player (default, always works)
  if (playerType === 'native') {
    // Show error message if src is invalid
    if (!isValidSrc) {
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error || 'No video source provided'}
            </Typography>
          </Box>
        </Box>
      );
    }
    
    return (
      <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              zIndex: 1,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fff' }}>
              Loading...
            </Typography>
          </Box>
        )}
        {error && !loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error}
            </Typography>
          </Box>
        )}
        <video
          ref={videoRef}
          src={src}
          controls={controls}
          muted={muted}
          playsInline={playsInline}
          preload={preload}
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            backgroundColor: '#000',
          }}
          onLoadedMetadata={() => {
            console.debug('[VideoPlayer] onLoadedMetadata fired');
            setLoading(false);
            setError(null);
            if (onReady) onReady();
          }}
          onLoadedData={() => {
            console.debug('[VideoPlayer] onLoadedData fired, readyState:', videoRef.current?.readyState);
            // Also clear loading on loadeddata as a backup
            if (videoRef.current && videoRef.current.readyState >= 2) {
              setLoading(false);
              setError(null);
            }
          }}
          onCanPlay={() => {
            console.debug('[VideoPlayer] onCanPlay fired');
            // Clear loading when video can play
            setLoading(false);
            setError(null);
          }}
          onLoadStart={() => {
            console.debug('[VideoPlayer] onLoadStart fired');
            setLoading(true);
            setError(null);
            if (onLoadStart) onLoadStart();
          }}
          onPlay={() => {
            setIsPlaying(true);
            setShowOverlay(true);
          }}
          onPause={() => {
            setIsPlaying(false);
            setShowOverlay(true);
          }}
          onEnded={() => {
            console.debug('[VideoPlayer] onEnded fired');
            setIsPlaying(false);
            setShowOverlay(true);
            if (onEnded) onEnded();
          }}
          onMouseEnter={() => setShowOverlay(true)}
          onMouseLeave={() => setShowOverlay(false)}
          onError={(e) => {
            console.error('[VideoPlayer] onError fired:', e);
            setLoading(false);
            const video = e.currentTarget;
            const videoError = video.error;
            let errorMessage = 'Video failed to load';
            if (videoError) {
              switch (videoError.code) {
                case videoError.MEDIA_ERR_ABORTED:
                  errorMessage = 'Video loading aborted';
                  break;
                case videoError.MEDIA_ERR_NETWORK:
                  errorMessage = 'Network error while loading video';
                  break;
                case videoError.MEDIA_ERR_DECODE:
                  errorMessage = 'Video decoding error';
                  break;
                case videoError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                  errorMessage = 'Video format not supported';
                  break;
                default:
                  errorMessage = `Video error: ${videoError.message || 'Unknown error'}`;
              }
            }
            setError(errorMessage);
            if (onError) {
              onError(videoError || e);
            }
          }}
        />
      </Box>
    );
  }

  // mpegts.js player for .ts files (lightweight, uses native video element)
  // Note: When using mpegts.js, we don't set src on the video element
  // because mpegts.js handles the source loading itself
  if (playerType === 'mpegts') {
    if (!isValidSrc) {
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error || 'No video source provided'}
            </Typography>
          </Box>
        </Box>
      );
    }

    return (
      <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              zIndex: 1,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fff' }}>
              Loading...
            </Typography>
          </Box>
        )}
        {error && !loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error}
            </Typography>
          </Box>
        )}
        <video
          ref={videoRef}
          controls={controls}
          muted={muted}
          playsInline={playsInline}
          preload="none"
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            backgroundColor: '#000',
          }}
          onPlay={() => {
            setIsPlaying(true);
            setShowOverlay(true);
          }}
          onPause={() => {
            setIsPlaying(false);
            setShowOverlay(true);
          }}
          onEnded={() => {
            console.debug('[VideoPlayer] mpegts.js video ended');
            setIsPlaying(false);
            setShowOverlay(true);
            if (onEnded) onEnded();
          }}
          onMouseEnter={() => setShowOverlay(true)}
          onMouseLeave={() => setShowOverlay(false)}
          onError={(e) => {
            // Suppress native video element errors when using mpegts.js
            // mpegts.js handles all loading and errors, so native errors are expected
            // and should be ignored (mpegts.js will report its own errors via its event handlers)
            const video = e.currentTarget;
            if (playerType === 'mpegts') {
              // mpegts.js is being used, ignore native video errors
              // The video element doesn't have src set, so errors are expected
              console.debug('[VideoPlayer] Ignoring native video error (mpegts.js is handling playback):', video.error?.code || 'unknown');
              return;
            }
            // If mpegts.js is not active, handle the error normally
            console.error('[VideoPlayer] Native video error (mpegts.js not active):', e);
            setLoading(false);
            const videoError = video.error;
            let errorMessage = 'Video failed to load';
            if (videoError) {
              switch (videoError.code) {
                case videoError.MEDIA_ERR_ABORTED:
                  errorMessage = 'Video loading aborted';
                  break;
                case videoError.MEDIA_ERR_NETWORK:
                  errorMessage = 'Network error while loading video';
                  break;
                case videoError.MEDIA_ERR_DECODE:
                  errorMessage = 'Video decoding error';
                  break;
                case videoError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                  errorMessage = 'Video format not supported';
                  break;
                default:
                  errorMessage = `Video error: ${videoError.message || 'Unknown error'}`;
              }
            }
            setError(errorMessage);
            if (onError) {
              onError(videoError || e);
            }
          }}
        />
        {/* Play/Pause Overlay Button - Centered */}
        {!loading && !error && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              pointerEvents: 'none',
              opacity: showOverlay ? 1 : 0,
              transition: 'opacity 0.3s ease-in-out',
            }}
          >
            <IconButton
              onClick={(e) => {
                e.stopPropagation();
                if (isPlaying) {
                  if (mpegtsPlayerRef.current) {
                    mpegtsPlayerRef.current.pause();
                  } else if (videoRef.current) {
                    videoRef.current.pause();
                  }
                } else {
                  if (mpegtsPlayerRef.current) {
                    mpegtsPlayerRef.current.play();
                  } else if (videoRef.current) {
                    videoRef.current.play();
                  }
                }
              }}
              sx={{
                pointerEvents: 'auto',
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                color: '#fff',
                width: 64,
                height: 64,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  transform: 'scale(1.1)',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              {isPlaying ? (
                <PauseIcon sx={{ fontSize: 40 }} />
              ) : (
                <PlayArrowIcon sx={{ fontSize: 40 }} />
              )}
            </IconButton>
          </Box>
        )}
      </Box>
    );
  }

  // Video.js player
  if (playerType === 'videojs') {
    if (!isValidSrc) {
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error || 'No video source provided'}
            </Typography>
          </Box>
        </Box>
      );
    }

    if (!VideoJS) {
      // Fallback to native while loading
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <video
            ref={videoRef}
            src={src}
            controls={controls}
            muted={muted}
            playsInline={playsInline}
            preload={preload}
            style={{ width: '100%', height: '100%', display: 'block', backgroundColor: '#000' }}
          />
        </Box>
      );
    }

    return (
      <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              zIndex: 1,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fff' }}>
              Loading...
            </Typography>
          </Box>
        )}
        {error && !loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error}
            </Typography>
          </Box>
        )}
        <div data-vjs-player>
          <video
            ref={playerType === 'videojs' ? videoRefCallback : videoRef}
            className="video-js vjs-theme-sea"
            playsInline={playsInline}
            preload={preload}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </Box>
    );
  }

  // React Player
  if (playerType === 'react-player') {
    if (!isValidSrc) {
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error || 'No video source provided'}
            </Typography>
          </Box>
        </Box>
      );
    }

    if (!ReactPlayerComponent) {
      // Fallback to native while loading
      return (
        <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
          <video
            ref={videoRef}
            src={src}
            controls={controls}
            muted={muted}
            playsInline={playsInline}
            preload={preload}
            style={{ width: '100%', height: '100%', display: 'block', backgroundColor: '#000' }}
          />
        </Box>
      );
    }

    return (
      <Box sx={{ position: 'relative', width, height, backgroundColor: '#000' }}>
        {loading && !light && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              zIndex: 1,
            }}
          >
            <Typography variant="caption" sx={{ color: '#fff' }}>
              Loading...
            </Typography>
          </Box>
        )}
        {error && !loading && !light && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              zIndex: 1,
            }}
          >
            <Typography variant="body2" sx={{ color: '#fff', textAlign: 'center', p: 2 }}>
              {error}
            </Typography>
          </Box>
        )}
        <ReactPlayerComponent
          url={src}
          width="100%"
          height="100%"
          controls={controls}
          playing={false}
          muted={muted}
          playsinline={playsInline}
          pip={false}
          stopOnUnmount={false}
          light={light}
          playIcon={playIcon}
          onReady={() => {
            setLoading(false);
            setError(null);
            if (onReady) onReady();
          }}
          onStart={() => {
            setLoading(false);
            setError(null);
          }}
          onError={(error: unknown) => {
            setLoading(false);
            const errorMessage = error instanceof Error ? error.message : 'Video playback error';
            setError(errorMessage);
            if (onError) onError(error);
          }}
          onLoadStart={() => {
            setLoading(true);
            setError(null);
            if (onLoadStart) onLoadStart();
          }}
          onEnded={() => {
            if (onEnded) onEnded();
          }}
        />
      </Box>
    );
  }

  // Fallback (should never reach here)
  return null;
});

VideoPlayer.displayName = 'VideoPlayer';

export default VideoPlayer;
