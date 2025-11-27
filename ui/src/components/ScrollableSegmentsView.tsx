import React from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import { Segment, Flow } from '../types';
import SegmentMediaWidget from './SegmentMediaWidget';

interface ScrollableSegmentsViewProps {
  segments: Segment[];
  flow: Flow | null;
  totalSegments: number | null;
  loadingMore: boolean;
  autoPlayEnabled: boolean;
}

const ScrollableSegmentsView: React.FC<ScrollableSegmentsViewProps> = ({
  segments,
  flow,
  totalSegments,
  loadingMore,
  autoPlayEnabled,
}) => {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, flexWrap: 'wrap', gap: 1 }}>
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
      </Box>

      {/* Individual segment widgets */}
      {segments.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'row', // Left to right layout
            overflowX: 'auto',
            overflowY: 'hidden',
            pb: 2,
            gap: 0,
            scrollBehavior: 'smooth', // CSS smooth scrolling
            // Ensure first video stays on the left
            justifyContent: 'flex-start',
            alignItems: 'flex-start',
            '&::-webkit-scrollbar': {
              height: 8,
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: '#f1f1f1',
              borderRadius: 4,
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#888',
              borderRadius: 4,
              '&:hover': {
                backgroundColor: '#555',
              },
            },
          }}
          id="segments-container"
        >
          {segments.map((segment, index) => (
            <SegmentMediaWidget
              key={`${segment.object_id}-${index}`}
              segment={segment}
              flow={flow}
              width={280}
              height={157.5} // 16:9 aspect ratio
              isFirst={index === 0} // Pass flag to indicate first video
              autoPlayEnabled={autoPlayEnabled}
              segmentIndex={index}
            />
          ))}
        </Box>
      )}
    </Box>
  );
};

export default ScrollableSegmentsView;

