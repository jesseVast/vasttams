import React, { useState, useEffect, useMemo } from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import { Segment, Flow } from '../types';
import SegmentMediaWidget from './SegmentMediaWidget';
import { API_BASE_URL } from '../services/api';

interface MultiviewSegmentsViewProps {
  segments: Segment[];
  flow: Flow | null;
  totalSegments: number | null;
  loadingMore: boolean;
  autoPlayEnabled: boolean;
}

// Helper function to parse timerange start time
const parseTimerangeStart = (timerange: string | undefined): number => {
  if (!timerange) return 0;
  
  try {
    const cleanRange = timerange.trim().replace(/^[[(]|[)\]]+$/g, '');
    
    if (cleanRange.includes('_')) {
      const startStr = cleanRange.split('_')[0];
      
      if (startStr.includes(':')) {
        const [seconds, nanos] = startStr.split(':');
        const sec = parseInt(seconds || '0', 10) || 0;
        const nano = parseInt((nanos || '0').padEnd(9, '0').substring(0, 9), 10) || 0;
        return sec + (nano / 1e9);
      } else {
        return parseFloat(startStr) || 0;
      }
    }
    return 0;
  } catch (error) {
    console.debug('Failed to parse timerange:', timerange, error);
    return 0;
  }
};

// Helper function to parse timerange end time
const parseTimerangeEnd = (timerange: string | undefined): number | null => {
  if (!timerange) return null;
  
  try {
    const cleanRange = timerange.trim().replace(/^[[(]|[)\]]+$/g, '');
    
    if (cleanRange.includes('_')) {
      const parts = cleanRange.split('_');
      if (parts.length >= 2) {
        const endStr = parts[1];
        
        if (endStr.includes(':')) {
          const [seconds, nanos] = endStr.split(':');
          const sec = parseInt(seconds || '0', 10) || 0;
          const nano = parseInt((nanos || '0').padEnd(9, '0').substring(0, 9), 10) || 0;
          return sec + (nano / 1e9);
        } else {
          return parseFloat(endStr) || null;
        }
      }
    }
    return null;
  } catch (error) {
    console.debug('Failed to parse timerange end:', timerange, error);
    return null;
  }
};

const MultiviewSegmentsView: React.FC<MultiviewSegmentsViewProps> = ({
  segments,
  flow,
  totalSegments,
  loadingMore,
  autoPlayEnabled,
}) => {
  const [hlsManifestUrl, setHlsManifestUrl] = useState<string | null>(null);
  const [hlsManifestLoading, setHlsManifestLoading] = useState(false);
  const [hlsManifestError, setHlsManifestError] = useState<string | null>(null);

  // Check if flow is HLS-compatible
  const isHLSFlow = flow?.container === 'video/mp2t';
  // Temporarily disable proxy usage to test direct presigned URLs / CORS fixes
  const useProxyForHLS = false;
  const hlsPlaylistUrl = isHLSFlow && flow?.id 
    ? `${API_BASE_URL}/hls/flows/${flow.id}/playlist.m3u8${useProxyForHLS ? '' : '?use_proxy=false'}`
    : null;

  // Fetch HLS manifest once when flow changes
  useEffect(() => {
    if (!hlsPlaylistUrl) {
      setHlsManifestUrl(null);
      return;
    }

    setHlsManifestLoading(true);
    setHlsManifestError(null);

    // Get auth token
    const token = typeof window !== 'undefined' && window.localStorage
      ? window.localStorage.getItem('token')
      : null;

    // Fetch manifest as text
    fetch(hlsPlaylistUrl, {
      headers: token ? {
        'Authorization': `Bearer ${token}`
      } : {}
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch HLS manifest: ${response.statusText}`);
        }
        return response.text();
      })
      .then(manifestText => {
        let modifiedManifest = manifestText;
        if (useProxyForHLS && token) {
          // Add access_token to all proxy segment URLs when proxying is enabled
          modifiedManifest = manifestText.replace(
            /(\/segments\/[^?\s]+\?url=[^&\s]+)(&[^\s]*)?/g,
            (match, urlPart, existingParams) => {
              if (match.includes('access_token=')) {
                return match;
              }
              const separator = existingParams ? '&' : (urlPart.includes('?') ? '&' : '?');
              return `${urlPart}${separator}access_token=${encodeURIComponent(token)}${existingParams || ''}`;
            }
          );
        }
        
        // Create a blob URL from the modified manifest content
        // This allows all players to use the same cached manifest with auth
        // Note: The manifest itself is only loaded once, but each hls.js player instance
        // will independently request segments from the manifest as needed for playback
        const blob = new Blob([modifiedManifest], { type: 'application/vnd.apple.mpegurl' });
        const blobUrl = URL.createObjectURL(blob);
        setHlsManifestUrl(blobUrl);
        setHlsManifestLoading(false);
        console.debug('[MultiviewSegmentsView] HLS manifest fetched once, modified with auth, and cached as blob URL');
        console.debug('[MultiviewSegmentsView] Note: Each hls.js player will independently request segments from the manifest as needed');
      })
      .catch(error => {
        console.error('[MultiviewSegmentsView] Failed to fetch HLS manifest:', error);
        setHlsManifestError(error.message);
        setHlsManifestLoading(false);
      });
  }, [hlsPlaylistUrl]);

  // Cleanup blob URL when component unmounts or manifest URL changes
  useEffect(() => {
    return () => {
      if (hlsManifestUrl) {
        URL.revokeObjectURL(hlsManifestUrl);
      }
    };
  }, [hlsManifestUrl]);

  // Calculate time offsets and durations for each segment
  const segmentTimeOffsets = useMemo(() => {
    return segments.map(segment => parseTimerangeStart(segment.timerange?.value));
  }, [segments]);
  
  const segmentDurations = useMemo(() => {
    return segments.map(segment => {
      const start = parseTimerangeStart(segment.timerange?.value);
      const end = parseTimerangeEnd(segment.timerange?.value);
      if (end !== null && end > start) {
        return end - start;
      }
      return null; // Duration unknown
    });
  }, [segments]);
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {totalSegments !== null 
            ? `${segments.length}/${totalSegments} segments`
            : `${segments.length} segment${segments.length !== 1 ? 's' : ''}${loadingMore ? '...' : ''}`
          }
        </Typography>
        {loadingMore && totalSegments !== null && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LinearProgress 
              variant="determinate"
              value={(segments.length / totalSegments) * 100}
              sx={{ width: 150, height: 6 }}
            />
            <Typography variant="caption" color="text.secondary">
              {Math.round((segments.length / totalSegments) * 100)}%
            </Typography>
          </Box>
        )}
        {hlsManifestLoading && (
          <Typography variant="caption" color="text.secondary">
            Loading HLS manifest...
          </Typography>
        )}
        {hlsManifestError && (
          <Typography variant="caption" color="error">
            HLS Error: {hlsManifestError}
          </Typography>
        )}
      </Box>

      {/* Grid layout for multiview - 3-4 videos horizontally, vertical scrolling */}
      {segments.length > 0 && (
        <Box
          sx={{
            display: 'grid',
            gap: 1.5,
            gridTemplateColumns: {
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              md: 'repeat(3, 1fr)',
              lg: 'repeat(4, 1fr)',
              xl: 'repeat(4, 1fr)', // Max 4 columns even on xl screens
            },
            gridAutoRows: 'auto', // Auto height rows
            overflowY: 'auto', // Allow vertical scrolling
            overflowX: 'hidden', // No horizontal scrolling
            maxHeight: 'calc(100vh - 280px)', // Fit viewport minus header/filters
            '& > *': {
              minHeight: 0,
              overflow: 'hidden',
            },
          }}
        >
          {segments.map((segment, index) => (
            <Box 
              key={`${segment.object_id}-${index}`}
              sx={{
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
                overflow: 'hidden',
              }}
            >
              <SegmentMediaWidget
                key={`${segment.object_id}-${index}-${hlsManifestUrl ? 'hls' : 'normal'}`}
                segment={segment}
                flow={flow}
                width="100%" // Use 100% width to fit grid cell
                height="auto" // Auto height to maintain aspect ratio
                isFirst={false}
                autoPlayEnabled={autoPlayEnabled}
                segmentIndex={index}
                loadImmediately={true} // Load all videos immediately in multiview
                // HLS-specific props
                useHLS={isHLSFlow && !!hlsManifestUrl}
                hlsManifestUrl={hlsManifestUrl}
                hlsStartTime={segmentTimeOffsets[index]}
                hlsSegmentDuration={segmentDurations[index] || undefined}
              />
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default MultiviewSegmentsView;

