import React, { useRef, useEffect, useState } from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
// Import CSS for video players (only loaded when used)
import 'video.js/dist/video-js.css';
import '@videojs/themes/dist/sea/index.css';

export type VideoPlayerType = 'videojs' | 'react-player' | 'native' | 'mpegts' | 'hls';

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
  onPlay?: () => void; // Called when video actually starts playing
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
  onPlay,
  onEnded,
  light = false,
  playIcon,
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Expose play/pause/stop methods via ref
  React.useImperativeHandle(ref, () => ({
    play: () => {
      if (playerType === 'native' && videoRef.current) {
        return videoRef.current.play();
      } else if (playerType === 'videojs' && videojsRef.current) {
        return videojsRef.current.play();
      } else if (playerType === 'hls' && videoRef.current) {
        // For hls.js, just call play() on the video element - let it handle everything
        return videoRef.current.play();
      } else if (playerType === 'mpegts' && videoRef.current) {
        // For mpegts.js, ensure player is ready before playing
        const video = videoRef.current;
        if (mpegtsPlayerRef.current && video.readyState >= 2) {
          return video.play();
        } else if (video.readyState >= 2) {
          // Try to play even if player ref isn't set (might still work)
          return video.play();
        } else {
          console.debug('[VideoPlayer] mpegts video not ready yet, waiting for canplay');
          // Wait for video to be ready
          return new Promise<void>((resolve, reject) => {
            const handleCanPlay = () => {
              video.removeEventListener('canplay', handleCanPlay);
              video.play().then(resolve).catch(reject);
            };
            video.addEventListener('canplay', handleCanPlay, { once: true });
            // Timeout after 5 seconds
            setTimeout(() => {
              video.removeEventListener('canplay', handleCanPlay);
              reject(new Error('mpegts video play timeout'));
            }, 5000);
          });
        }
      }
      return Promise.resolve();
    },
    pause: () => {
      if (playerType === 'native' && videoRef.current) {
        videoRef.current.pause();
      } else if (playerType === 'videojs' && videojsRef.current) {
        videojsRef.current.pause();
      } else if (playerType === 'hls' && videoRef.current) {
        videoRef.current.pause();
      } else if (playerType === 'mpegts' && videoRef.current) {
        // For mpegts.js, call pause() on the video element
        videoRef.current.pause();
      }
    },
    stop: () => {
      if (playerType === 'native' && videoRef.current) {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      } else if (playerType === 'videojs' && videojsRef.current) {
        videojsRef.current.pause();
        videojsRef.current.currentTime(0);
      } else if (playerType === 'hls' && videoRef.current) {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      } else if (playerType === 'mpegts' && videoRef.current) {
        // For mpegts.js, call pause() and reset currentTime on the video element
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
    },
    getVideoElement: () => videoRef.current,
    getHlsPlayer: () => hlsPlayerRef.current
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
  const [HlsJSLoaded, setHlsJSLoaded] = useState<boolean>(false);
  const mpegtsPlayerRef = useRef<any>(null);
  const hlsPlayerRef = useRef<any>(null);
  const hlsJSRef = useRef<any>(null); // Store Hls class in ref to avoid React state reducer issues

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

  // Lazy load hls.js
  useEffect(() => {
    if (playerType === 'hls' && !hlsJSRef.current) {
      import('hls.js').then((hlsModule) => {
        // hls.js exports Hls class as default export
        // Store in ref to avoid React state reducer processing the class
        hlsJSRef.current = hlsModule.default || hlsModule;
        setHlsJSLoaded(true);
      });
    }
  }, [playerType]);

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

  // Initialize mpegts.js player for .ts files - SIMPLIFIED VERSION
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
        // Minimal mpegts.js configuration
        const player = MpegtsJS.createPlayer({
          type: 'mpegts',
          url: src,
          isLive: false,
          cors: true,
          withCredentials: false,
        }, {
          enableWorker: true,
        });

        player.attachMediaElement(video);
        player.load();
        mpegtsPlayerRef.current = player;

        // Only handle fatal errors
        player.on(MpegtsJS.Events.ERROR, (errorType: string, errorDetail: any, errorInfo: any) => {
          console.error('[VideoPlayer] mpegts.js error:', {
            errorType,
            errorDetail,
            src: src.substring(0, 150),
          });
          
          let errorMessage = `mpegts.js error: ${errorType}`;
          if (errorDetail) {
            if (errorDetail.msg) {
              errorMessage += ` - ${errorDetail.msg}`;
            } else if (typeof errorDetail === 'string') {
              errorMessage += ` - ${errorDetail}`;
            }
          }
          
          setLoading(false);
          setError(errorMessage);
          if (onError) {
            onError(new Error(errorMessage));
          }
        });

        // Autoplay function for mpegts player
        const attemptAutoplay = () => {
          if (video && video.readyState >= 2 && video.paused) {
            console.debug('[VideoPlayer] Attempting autoplay for mpegts player');
            video.play()
              .then(() => {
                console.debug('[VideoPlayer] mpegts player autoplay successful');
              })
              .catch((error: any) => {
                // Autoplay may be blocked by browser - this is expected in some cases
                console.debug('[VideoPlayer] mpegts player autoplay prevented (may require user interaction):', error);
              });
          }
        };

        // Simple ready handler - clear loading and autoplay for mpegts
        const handleLoadedMetadata = () => {
          console.debug('[VideoPlayer] mpegts.js metadata loaded');
          setLoading(false);
          setError(null);
          if (onReady) onReady();
          
          // Autoplay for mpegts player - attempt to play when ready
          // This is specifically for mpegts as requested (native HTML5 is fine)
          attemptAutoplay();
        };

        // Also try autoplay on canplay event as fallback
        const handleCanPlay = () => {
          console.debug('[VideoPlayer] mpegts.js canplay event');
          attemptAutoplay();
        };

        video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
        video.addEventListener('canplay', handleCanPlay, { once: true });

        // Cleanup on unmount
        return () => {
          video.removeEventListener('loadedmetadata', handleLoadedMetadata);
          video.removeEventListener('canplay', handleCanPlay);
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

  // Initialize hls.js player for .ts files - SIMPLIFIED VERSION
  useEffect(() => {
    const HlsJS = hlsJSRef.current;
    
    if (playerType !== 'hls' || !HlsJS || !videoRef.current || !isValidSrc) {
      // Cleanup if switching away from hls
      if (hlsPlayerRef.current) {
        try {
          hlsPlayerRef.current.destroy();
        } catch (err) {
          console.debug('Error destroying hls player:', err);
        }
        hlsPlayerRef.current = null;
      }
      return;
    }

    const video = videoRef.current;
    
    // Cleanup existing player
    if (hlsPlayerRef.current) {
      try {
        hlsPlayerRef.current.destroy();
      } catch (err) {
        console.debug('Error destroying hls player:', err);
      }
      hlsPlayerRef.current = null;
    }
    
    // Check if hls.js is supported
    // HlsJS is the Hls class from hls.js, stored in ref
    if (HlsJS && typeof HlsJS.isSupported === 'function' && HlsJS.isSupported()) {
      console.debug('[VideoPlayer] Initializing hls.js player');
      setLoading(true);
      setError(null);
      if (onLoadStart) onLoadStart();

      try {
        // Minimal hls.js configuration - let it use defaults
        // HlsJS is the Hls class from hls.js, must use 'new' keyword
        const Hls = HlsJS;
        const hls = new Hls({
          enableWorker: true,
          // Enable fragment caching to reduce repeated requests
          maxBufferLength: 30, // Keep 30 seconds of buffer
          maxMaxBufferLength: 60, // Max 60 seconds
        });

        console.debug('[VideoPlayer] Loading HLS manifest (blob URL, cached in memory):', src.substring(0, 100));
        hls.loadSource(src);
        hls.attachMedia(video);
        hlsPlayerRef.current = hls;
        
        // Log when segments are requested (to help debug repeated requests)
        hls.on(Hls.Events.FRAG_LOADING, (event: any, data: any) => {
          console.debug('[VideoPlayer] hls.js requesting segment:', {
            url: data.frag?.url?.substring(0, 100),
            sn: data.frag?.sn,
            level: data.frag?.level,
          });
        });

        // Only handle fatal errors
        // Use Hls.Events for event constants
        hls.on(Hls.Events.ERROR, (event: any, data: any) => {
          if (data.fatal) {
            console.error('[VideoPlayer] hls.js fatal error:', {
              type: data.type,
              details: data.details,
              src: src.substring(0, 150),
            });
            
            let errorMessage = `hls.js error: ${data.type}`;
            if (data.details) {
              errorMessage += ` - ${data.details}`;
            }
            
            setLoading(false);
            setError(errorMessage);
            if (onError) {
              onError(new Error(errorMessage));
            }
          }
          // Ignore non-fatal errors - let hls.js handle them
        });

        // Handle manifest parsed - this is when we can safely seek
        hls.on(Hls.Events.MANIFEST_PARSED, (event: any, data: any) => {
          console.debug('[VideoPlayer] hls.js manifest parsed', {
            levels: data.levels?.length,
            firstLevelDuration: data.levels?.[0]?.duration,
          });
          setLoading(false);
          if (onReady) {
            // Call onReady after manifest is parsed so seeking can happen
            onReady();
          }
        });

        // Also handle LEVEL_LOADED for when segments are ready
        hls.on(Hls.Events.LEVEL_LOADED, (event: any, data: any) => {
          console.debug('[VideoPlayer] hls.js level loaded', {
            level: data.level,
            details: data.details?.length,
          });
          if (loading) {
            setLoading(false);
            if (onReady) onReady();
          }
        });
        
        // Handle when media is attached and ready
        hls.on(Hls.Events.MEDIA_ATTACHED, () => {
          console.debug('[VideoPlayer] hls.js media attached');
        });
        
        // Handle when first fragment is loaded (playback can start)
        hls.on(Hls.Events.FRAG_LOADED, (event: any, data: any) => {
          console.debug('[VideoPlayer] hls.js fragment loaded', {
            frag: data.frag?.sn,
            type: data.frag?.type,
          });
        });

        // Simple ready handler - fallback for metadata loaded
        const handleLoadedMetadata = () => {
          console.debug('[VideoPlayer] hls.js metadata loaded');
          if (loading) {
            setLoading(false);
            setError(null);
            if (onReady) onReady();
          }
        };

        video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });

        // Cleanup on unmount
        return () => {
          video.removeEventListener('loadedmetadata', handleLoadedMetadata);
          if (hlsPlayerRef.current) {
            try {
              hlsPlayerRef.current.destroy();
            } catch (err) {
              console.debug('Error destroying hls player on cleanup:', err);
            }
            hlsPlayerRef.current = null;
          }
        };
      } catch (err) {
        console.error('[VideoPlayer] Failed to initialize hls.js:', err);
        setLoading(false);
        const errorMessage = `Failed to initialize hls.js: ${err instanceof Error ? err.message : 'Unknown error'}`;
        setError(errorMessage);
        if (onError) {
          onError(err);
        }
      }
    } else {
      console.warn('[VideoPlayer] hls.js is not supported in this browser');
      setLoading(false);
      setError('hls.js is not supported in this browser');
      if (onError) {
        onError(new Error('hls.js is not supported'));
      }
    }
  }, [playerType, HlsJSLoaded, src, isValidSrc, onReady, onError, onLoadStart]);

  // Sync playing state with video element - SIMPLIFIED for mpegts
  // Only sync for native and hls players, let mpegts handle its own state
  useEffect(() => {
    if (!videoRef.current) return;
    // Skip sync for mpegts - let it handle playback state naturally
    if (playerType === 'mpegts') return;
    
    const video = videoRef.current;
    
    const updatePlayingState = () => {
      // Only update if video is actually playing (not just showing first frame)
      const actuallyPlaying = !video.paused && (video.readyState >= 2);
      if (actuallyPlaying !== isPlaying) {
        setIsPlaying(actuallyPlaying);
      }
    };
    
    // Initial state
    updatePlayingState();
    
    // Listen to playing/pause events (use 'playing' not 'play' to detect actual playback)
    const handlePlaying = () => {
      setIsPlaying(true);
    };
    const handlePause = () => {
      setIsPlaying(false);
    };
    
    video.addEventListener('playing', handlePlaying);
    video.addEventListener('pause', handlePause);
    
    return () => {
      video.removeEventListener('playing', handlePlaying);
      video.removeEventListener('pause', handlePause);
    };
  }, [playerType, src, isPlaying]);

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

  // Shared video element props and handlers for both native and mpegts players
  const sharedVideoProps = {
    ref: videoRef,
    controls: false, // Always false - we use custom controls widget
    muted,
    playsInline,
    style: {
      width: '100%',
      height: '100%',
      display: 'block' as const,
      backgroundColor: '#000',
    },
    onPlaying: () => {
      // Use 'playing' event which fires when playback actually starts (not just when play() is called)
      console.debug('[VideoPlayer] Video actually playing');
      setIsPlaying(true);
      setShowOverlay(true);
      if (onPlay) onPlay();
    },
    onPause: () => {
      setIsPlaying(false);
      setShowOverlay(true);
    },
    onEnded: () => {
      console.debug('[VideoPlayer] Video ended');
      setIsPlaying(false);
      setShowOverlay(true);
      if (onEnded) onEnded();
    },
  };

  // Shared error handler for native player
  const handleNativeError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
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
  };

  // Shared loading/error overlay component
  const renderOverlays = () => (
    <>
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
    </>
  );

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
        {renderOverlays()}
        <video
          {...sharedVideoProps}
          src={src}
          preload={preload}
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
          onError={(e) => {
            console.error('[VideoPlayer] onError fired:', e);
            setLoading(false);
            handleNativeError(e);
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
        {renderOverlays()}
        <video
          {...sharedVideoProps}
          preload="none"
          onError={(e) => {
            // Suppress native video element errors when using mpegts.js
            // mpegts.js handles all loading and errors, so native errors are expected
            // and should be ignored (mpegts.js will report its own errors via its event handlers)
            const video = e.currentTarget;
            // mpegts.js is being used, ignore native video errors
            // The video element doesn't have src set, so errors are expected
            console.debug('[VideoPlayer] Ignoring native video error (mpegts.js is handling playback):', video.error?.code || 'unknown');
          }}
        />
      </Box>
    );
  }

  // hls.js player rendering - use shared props like native player
  if (playerType === 'hls') {
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
        {renderOverlays()}
        <video
          {...sharedVideoProps}
          preload="none"
          onError={(e) => {
            // Suppress native video element errors when using hls.js
            // hls.js handles all loading and errors
            console.debug('[VideoPlayer] Ignoring native video error (hls.js is handling playback)');
          }}
        />
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
            {...sharedVideoProps}
            src={src}
            preload={preload}
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

