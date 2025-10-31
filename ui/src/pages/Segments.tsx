import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container,
  Typography,
  TextField,
  CircularProgress,
  Box,
  Chip,
  Card,
  CardContent,
  Button,
  Paper,
  IconButton,
} from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';
import SearchIcon from '@mui/icons-material/Search';
import { Segment, Flow } from '../types';
import { segmentService, flowService } from '../services/api';
import SegmentMediaWidget from '../components/SegmentMediaWidget';

const Segments: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [filterFlowId, setFilterFlowId] = useState<string>(searchParams.get('flow_id') || '');
  const [loading, setLoading] = useState(false);
  const [filteredFlow, setFilteredFlow] = useState<Flow | null>(null);
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');

  useEffect(() => {
    // Read initial flow_id from URL
    const flowIdParam = searchParams.get('flow_id');
    if (flowIdParam && flowIdParam !== filterFlowId) {
      setFilterFlowId(flowIdParam);
    }
  }, []);

  useEffect(() => {
    // Update URL when filter changes
    if (filterFlowId) {
      setSearchParams({ flow_id: filterFlowId }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
      setFilteredFlow(null);
      setSegments([]);
    }
  }, [filterFlowId, setSearchParams]);

  const loadFlowDetails = async () => {
    if (!filterFlowId) return;
    try {
      const flow = await flowService.get(filterFlowId);
      setFilteredFlow(flow);
    } catch (error) {
      console.error('Failed to load flow details:', error);
      setFilteredFlow(null);
    }
  };

  // Convert user input to TAMS timerange format
  const buildTimerange = (start: string, end: string): string | undefined => {
    if (!start && !end) return undefined;
    
    let timerange = '';
    
    if (start) {
      // Normalize start time: ensure format is seconds:nanoseconds
      const normalizedStart = normalizeTimeInput(start);
      timerange = `[${normalizedStart}`;
    } else {
      timerange = '(';
    }
    
    timerange += '_';
    
    if (end) {
      // Normalize end time
      const normalizedEnd = normalizeTimeInput(end);
      timerange += `${normalizedEnd})`;
    } else {
      timerange += ')';
    }
    
    return timerange;
  };

  // Normalize time input to TAMS format (seconds:nanoseconds)
  // Accepts formats like: "10", "10:0", "10:500000000" (for half a second in nanoseconds)
  const normalizeTimeInput = (input: string): string => {
    if (!input) return '';
    
    // Remove any whitespace
    input = input.trim();
    
    // If it contains a colon, assume it's already in seconds:nanoseconds format
    if (input.includes(':')) {
      const parts = input.split(':');
      if (parts.length === 2) {
        const seconds = parts[0];
        const nanoseconds = parts[1].padEnd(9, '0').substring(0, 9); // Ensure 9 digits
        return `${seconds}:${nanoseconds}`;
      }
    }
    
    // If it's just a number, treat as seconds
    const numValue = parseFloat(input);
    if (!isNaN(numValue)) {
      const seconds = Math.floor(numValue);
      const fractionalPart = numValue - seconds;
      const nanoseconds = Math.floor(fractionalPart * 1000000000);
      return `${seconds}:${nanoseconds.toString().padStart(9, '0')}`;
    }
    
    // Return as-is if we can't parse it
    return input;
  };

  const loadSegments = useCallback(async () => {
    if (!filterFlowId) return;
    
    try {
      setLoading(true);
      const timerange = buildTimerange(startTime, endTime);
      const data = await segmentService.listByFlow(filterFlowId, timerange);
      
      // Sort by sample_offset for chronological order
      const sorted = [...data].sort((a, b) => {
        const aOffset = a.sample_offset ?? -1;
        const bOffset = b.sample_offset ?? -1;
        return aOffset - bOffset;
      });
      
      setSegments(sorted);
    } catch (error) {
      console.error('Failed to load segments:', error);
      setSegments([]);
    } finally {
      setLoading(false);
    }
  }, [filterFlowId, startTime, endTime]);

  const handleSearch = () => {
    loadSegments();
  };

  const handleClearSearch = () => {
    setStartTime('');
    setEndTime('');
    // Trigger reload after clearing
    setTimeout(() => {
      loadSegments();
    }, 0);
  };

  // Initial load when filterFlowId is set
  useEffect(() => {
    if (filterFlowId) {
      setLoading(true);
      loadFlowDetails();
      // Load segments with current time filters
      const timerange = buildTimerange(startTime, endTime);
      segmentService.listByFlow(filterFlowId, timerange)
        .then(data => {
          const sorted = [...data].sort((a, b) => {
            const aOffset = a.sample_offset ?? -1;
            const bOffset = b.sample_offset ?? -1;
            return aOffset - bOffset;
          });
          setSegments(sorted);
        })
        .catch(error => {
          console.error('Failed to load segments:', error);
          setSegments([]);
        })
        .finally(() => {
          setLoading(false);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterFlowId]);

  return (
    <Container maxWidth={false}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Segments
        </Typography>
      </Box>

      {filteredFlow && (
        <Paper sx={{ p: 1.5, mb: 2, backgroundColor: '#f5f5f5' }}>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold', minWidth: 60 }}>
              Flow:
            </Typography>
            <Chip label={filteredFlow.id} size="small" variant="outlined" />
            {filteredFlow.label && (
              <Chip label={filteredFlow.label} size="small" variant="outlined" />
            )}
            <Chip label={filteredFlow.format} size="small" variant="outlined" color="primary" />
            {filteredFlow.codec && (
              <Chip label={filteredFlow.codec} size="small" variant="outlined" color="secondary" />
            )}
            {filteredFlow.container && (
              <Chip label={filteredFlow.container} size="small" variant="outlined" />
            )}
            {filteredFlow.essence_parameters?.frame_width && filteredFlow.essence_parameters?.frame_height && (
              <Chip 
                label={`${filteredFlow.essence_parameters.frame_width}x${filteredFlow.essence_parameters.frame_height}`} 
                size="small" 
                variant="outlined"
              />
            )}
            {filteredFlow.essence_parameters?.frame_rate && (
              <Chip 
                label={`${filteredFlow.essence_parameters.frame_rate.value || 
                  (filteredFlow.essence_parameters.frame_rate.numerator && filteredFlow.essence_parameters.frame_rate.denominator
                    ? `${filteredFlow.essence_parameters.frame_rate.numerator}/${filteredFlow.essence_parameters.frame_rate.denominator}`
                    : 'N/A')} fps`} 
                size="small" 
                variant="outlined"
              />
            )}
            {filteredFlow.avg_bit_rate && (
              <Chip 
                label={`${(filteredFlow.avg_bit_rate / 1000).toFixed(1)} Mbps`} 
                size="small" 
                variant="outlined" 
                color="info"
              />
            )}
            {filteredFlow.generation && (
              <Chip label={`Gen ${filteredFlow.generation}`} size="small" variant="outlined" />
            )}
          </Box>
        </Paper>
      )}

      {/* Time Interval Search */}
      {filterFlowId && (
        <Paper sx={{ p: 1.5, mb: 2, backgroundColor: '#fafafa' }}>
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: 'wrap' }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold', minWidth: 80 }}>
              Time Range:
            </Typography>
            <TextField
              label="Start"
              placeholder="0:0"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              size="small"
              sx={{ width: 120 }}
              InputProps={{
                endAdornment: startTime ? (
                  <IconButton
                    size="small"
                    onClick={() => {
                      setStartTime('');
                      setTimeout(() => loadSegments(), 0);
                    }}
                    sx={{ mr: -1 }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                ) : null,
              }}
            />
            <Typography variant="caption" color="text.secondary">to</Typography>
            <TextField
              label="End"
              placeholder="100:0"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              size="small"
              sx={{ width: 120 }}
              InputProps={{
                endAdornment: endTime ? (
                  <IconButton
                    size="small"
                    onClick={() => {
                      setEndTime('');
                      setTimeout(() => loadSegments(), 0);
                    }}
                    sx={{ mr: -1 }}
                  >
                    <ClearIcon fontSize="small" />
                  </IconButton>
                ) : null,
              }}
            />
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              size="small"
            >
              Search
            </Button>
            {(startTime || endTime) && (
              <Button
                variant="outlined"
                startIcon={<ClearIcon />}
                onClick={handleClearSearch}
                size="small"
              >
                Clear
              </Button>
            )}
          </Box>
        </Paper>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading segments...</Typography>
        </Box>
      ) : segments.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, p: 4 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No segments found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', maxWidth: 500, mt: 1 }}>
            {filterFlowId 
              ? 'No segments match the current time interval search criteria. Try adjusting the start and end times.'
              : 'To view segments, please navigate to the Flows page and click "View Segments" on a flow to filter segments by that flow.'}
          </Typography>
        </Box>
      ) : (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" color="text.secondary">
              {segments.length} segment{segments.length !== 1 ? 's' : ''} found
            </Typography>
          </Box>
          <Box
            sx={{
              display: 'flex',
              overflowX: 'auto',
              overflowY: 'hidden',
              pb: 2,
              gap: 0,
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
          >
            {segments.map((segment, index) => (
              <SegmentMediaWidget
                key={`${segment.object_id}-${index}`}
                segment={segment}
                flow={filteredFlow}
                width={280}
                height={157.5} // 16:9 aspect ratio
              />
            ))}
          </Box>
        </Box>
      )}
    </Container>
  );
};

export default Segments;
