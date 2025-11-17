import React, { useRef, useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
// Import CSS for video players (only loaded when used)
import 'video.js/dist/video-js.css';
import '@videojs/themes/dist/sea/index.css';

export type VideoPlayerType = 'videojs' | 'react-player' | 'native';

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
  light?: boolean; // For react-player light mode (thumbnail preview)
  playIcon?: React.ReactNode; // For react-player light mode
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
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
  light = false,
  playIcon,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [loading, setLoading] = useState(true);

  // Lazy load other players only when needed
  const [ReactPlayerComponent, setReactPlayerComponent] = useState<React.ComponentType<any> | null>(null);
  const [VideoJS, setVideoJS] = useState<any>(null);

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

  // Video.js player initialization
  const videojsRef = useRef<any>(null);
  useEffect(() => {
    if (playerType === 'videojs' && VideoJS && videoRef.current && !videojsRef.current) {
      const player = VideoJS(videoRef.current, {
        controls,
        muted,
        preload,
        playsinline: playsInline,
        fluid: true,
        responsive: true,
        fill: true,
      });

      videojsRef.current = player;

      player.ready(() => {
        setLoading(false);
        if (onReady) onReady();
      });

      player.on('loadstart', () => {
        setLoading(true);
        if (onLoadStart) onLoadStart();
      });

      player.on('error', () => {
        setLoading(false);
        if (onError) {
          const error = player.error();
          onError(new Error(`Video.js error: ${error?.message || 'Unknown error'}`));
        }
      });

      return () => {
        if (videojsRef.current) {
          videojsRef.current.dispose();
          videojsRef.current = null;
        }
      };
    }
  }, [playerType, VideoJS, src, controls, muted, preload, playsInline, onReady, onError, onLoadStart]);

  // Update Video.js source when src changes
  useEffect(() => {
    if (playerType === 'videojs' && videojsRef.current && src) {
      videojsRef.current.src(src);
    }
  }, [src, playerType]);

  // Check if native video is already loaded when component mounts or src changes
  useEffect(() => {
    if (playerType === 'native' && videoRef.current && src) {
      const video = videoRef.current;
      
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
        }
      }, 5000); // 5 second timeout
      
      return () => clearTimeout(timeoutId);
    }
  }, [playerType, src, loading, onReady]);

  // Native HTML5 video player (default, always works)
  if (playerType === 'native') {
    
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
            if (onReady) onReady();
          }}
          onLoadedData={() => {
            console.debug('[VideoPlayer] onLoadedData fired, readyState:', videoRef.current?.readyState);
            // Also clear loading on loadeddata as a backup
            if (videoRef.current && videoRef.current.readyState >= 2) {
              setLoading(false);
            }
          }}
          onCanPlay={() => {
            console.debug('[VideoPlayer] onCanPlay fired');
            // Clear loading when video can play
            setLoading(false);
          }}
          onLoadStart={() => {
            console.debug('[VideoPlayer] onLoadStart fired');
            setLoading(true);
            if (onLoadStart) onLoadStart();
          }}
          onError={(e) => {
            console.error('[VideoPlayer] onError fired:', e);
            setLoading(false);
            if (onError) {
              const video = e.currentTarget;
              const error = video.error;
              onError(error || e);
            }
          }}
        />
      </Box>
    );
  }

  // Video.js player
  if (playerType === 'videojs') {
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
        <div data-vjs-player>
          <video
            ref={videoRef}
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
        <ReactPlayerComponent
          src={src}
          width="100%"
          height="100%"
          controls={controls}
          playing={false}
          muted={muted}
          playsInline={playsInline}
          pip={false}
          stopOnUnmount={false}
          light={light}
          playIcon={playIcon}
          onReady={() => {
            setLoading(false);
            if (onReady) onReady();
          }}
          onStart={() => {
            setLoading(false);
          }}
          onError={(error: unknown) => {
            setLoading(false);
            if (onError) onError(error);
          }}
          onLoadStart={() => {
            setLoading(true);
            if (onLoadStart) onLoadStart();
          }}
        />
      </Box>
    );
  }

  // Fallback (should never reach here)
  return null;
};

export default VideoPlayer;
