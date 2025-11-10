import React, { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import Hls from 'hls.js';

interface HLSPlayerProps {
  playlistUrl: string;
  width?: number | string;
  height?: number | string;
  autoPlay?: boolean;
}

const HLSPlayer: React.FC<HLSPlayerProps> = ({ 
  playlistUrl, 
  width = '100%', 
  height = 'auto',
  autoPlay = false 
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let hls: Hls | null = null;

    const initializePlayer = () => {
      if (Hls.isSupported()) {
        // Use hls.js for browsers that don't natively support HLS
        // Note: playlistUrl already includes access_token query parameter
        // Segment URLs are presigned S3 URLs and don't need authentication
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: false,
          backBufferLength: 90,
        });

        hls.loadSource(playlistUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          if (autoPlay) {
            video.play().catch((error) => {
              console.debug('HLS autoplay prevented:', error);
            });
          }
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.error('HLS network error, trying to recover...');
                hls?.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.error('HLS media error, trying to recover...');
                hls?.recoverMediaError();
                break;
              default:
                console.error('HLS fatal error, destroying player');
                hls?.destroy();
                break;
            }
          }
        });

        hlsRef.current = hls;
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        video.src = playlistUrl;
        if (autoPlay) {
          video.play().catch((error) => {
            console.debug('HLS autoplay prevented:', error);
          });
        }
      } else {
        console.error('HLS is not supported in this browser');
      }
    };

    initializePlayer();

    return () => {
      if (hls) {
        hls.destroy();
        hlsRef.current = null;
      }
    };
  }, [playlistUrl, autoPlay]);

  return (
    <Box sx={{ width: '100%', backgroundColor: '#000' }}>
      <video
        ref={videoRef}
        controls
        playsInline
        style={{
          width: width,
          height: height,
          display: 'block',
          maxWidth: '100%',
        }}
        preload="metadata"
        crossOrigin="anonymous"
      >
        Your browser does not support the video tag or HLS playback.
      </video>
    </Box>
  );
};

export default HLSPlayer;

