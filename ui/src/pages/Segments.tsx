import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container,
  Typography,
  TextField,
  CircularProgress,
  Box,
  Chip,
  Button,
  Paper,
  IconButton,
  LinearProgress,
} from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';
import SearchIcon from '@mui/icons-material/Search';
import { Segment, Flow } from '../types';
import { segmentService, flowService } from '../services/api';
import SegmentMediaWidget from '../components/SegmentMediaWidget';

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

const Segments: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [filterFlowId, setFilterFlowId] = useState<string>(searchParams.get('flow_id') || '');
  const [loading, setLoading] = useState(false);
  const [filteredFlow, setFilteredFlow] = useState<Flow | null>(null);
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [totalSegments, setTotalSegments] = useState<number | null>(null);
  const [estimatedTotal, setEstimatedTotal] = useState<number | null>(null); // Estimated count for placeholders

  useEffect(() => {
    // Read initial flow_id from URL
    const flowIdParam = searchParams.get('flow_id');
    if (flowIdParam && flowIdParam !== filterFlowId) {
      setFilterFlowId(flowIdParam);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

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
  const buildTimerange = useCallback((start: string, end: string): string | undefined => {
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
  }, []);

  // Parse TAMS timerange to extract start time in seconds (for sorting)
  // Format: [start_seconds:start_nanos_end_seconds:end_nanos) or [start_end)
  const parseTimerangeStart = (timerange: string | undefined): number => {
    if (!timerange) return 0;
    
    try {
      // Remove brackets/parentheses
      const cleanRange = timerange.trim().replace(/^[[(]|[)\]]+$/g, '');
      
      if (cleanRange.includes('_')) {
        // TAMS format: [start_end)
        const startStr = cleanRange.split('_')[0];
        
        // Parse start time (format: seconds:nanoseconds)
        if (startStr.includes(':')) {
          const [seconds, nanos] = startStr.split(':');
          const sec = parseInt(seconds || '0', 10) || 0;
          const nano = parseInt((nanos || '0').padEnd(9, '0').substring(0, 9), 10) || 0;
          return sec + (nano / 1e9);
        } else {
          // Just seconds
          return parseFloat(startStr) || 0;
        }
      } else if (cleanRange.includes(',')) {
        // Standard format: [start,end)
        const startStr = cleanRange.split(',')[0];
        return parseFloat(startStr) || 0;
      } else {
        // Single timestamp
        if (cleanRange.includes(':')) {
          const [seconds, nanos] = cleanRange.split(':');
          const sec = parseInt(seconds || '0', 10) || 0;
          const nano = parseInt((nanos || '0').padEnd(9, '0').substring(0, 9), 10) || 0;
          return sec + (nano / 1e9);
        }
        return parseFloat(cleanRange) || 0;
      }
    } catch (error) {
      console.debug('Failed to parse timerange:', timerange, error);
      return 0;
    }
  };

  // Sort segments by timerange start time
  const sortSegments = useCallback((data: Segment[]) => {
    return [...data].sort((a, b) => {
      const aHasTimerange = a.timerange?.value;
      const bHasTimerange = b.timerange?.value;
      
      // If both have timeranges, sort by timerange start time
      if (aHasTimerange && bHasTimerange) {
        const aStart = parseTimerangeStart(a.timerange.value);
        const bStart = parseTimerangeStart(b.timerange.value);
        return aStart - bStart;
      }
      
      // If only one has a timerange, prioritize it
      if (aHasTimerange && !bHasTimerange) return -1;
      if (!aHasTimerange && bHasTimerange) return 1;
      
      // If neither has timerange, fall back to sample_offset
      const aOffset = a.sample_offset ?? -1;
      const bOffset = b.sample_offset ?? -1;
      return aOffset - bOffset;
    });
  }, []);

  const loadSegments = useCallback(async () => {
    if (!filterFlowId) return;
    
    // Show loading page immediately
    setLoading(true);
    setSegments([]);
    setTotalSegments(null);
    setEstimatedTotal(null);
    setLoadingMore(false);
    
    // Performance instrumentation
    const perfId = `loadSegments-${Date.now()}`;
    const perfStartTime = performance.now();
    performance.mark(`${perfId}-start`);
    
    console.group(`🔍 [Segments] Loading segments for flow: ${filterFlowId}`);
    console.time(`${perfId}-total`);
    
    try {
      const timerange = buildTimerange(startTime, endTime);
      
      console.log(`[${perfId}] Timerange: ${timerange || 'none'}`);
      
      // Load initial batch to get estimate and show UI immediately
      const initialBatchSize = 50; // Load first 50 segments quickly
      const initialApiStart = performance.now();
      performance.mark(`${perfId}-initial-api-start`);
      console.log(`[${perfId}] Starting initial API call (limit=${initialBatchSize}, offset=0)...`);
      
      const initialBatch = await segmentService.listByFlow(filterFlowId, timerange, initialBatchSize, 0);
      
      const initialApiEnd = performance.now();
      performance.mark(`${perfId}-initial-api-end`);
      performance.measure(`${perfId}-initial-api`, `${perfId}-initial-api-start`, `${perfId}-initial-api-end`);
      console.log(`[${perfId}] Initial API call completed: ${(initialApiEnd - initialApiStart).toFixed(2)}ms, received ${initialBatch.length} segments`);
      
      // Estimate total: if we got a full batch, there are likely more
      const estimated = initialBatch.length === initialBatchSize ? initialBatchSize * 10 : initialBatch.length;
      setEstimatedTotal(estimated);
      setTotalSegments(null); // Will be set when we know the actual total
      
      // Show UI with initial batch
      const sortStart = performance.now();
      const sortedInitial = sortSegments(initialBatch);
      const sortEnd = performance.now();
      console.log(`[${perfId}] Sorting initial batch: ${(sortEnd - sortStart).toFixed(2)}ms`);
      
      const setStateStart = performance.now();
      setSegments(sortedInitial);
      setLoading(false); // Hide loading page, show segments
      setLoadingMore(true); // Show loading indicator in scroll bar
      const setStateEnd = performance.now();
      console.log(`[${perfId}] State update (setSegments, show UI): ${(setStateEnd - setStateStart).toFixed(2)}ms`);
      console.log(`[${perfId}] UI displayed after: ${(setStateEnd - perfStartTime).toFixed(2)}ms`);
      
      // Load remaining segments in background
      if (initialBatch.length > 0) {
        const backgroundStart = performance.now();
        console.log(`[${perfId}] Starting background loading...`);
        
        // Load all remaining segments using pagination (max 1000 per request)
        // Fetch in batches of 1000 until we get fewer than requested
        let allSegments = [...initialBatch];
        let offset = initialBatch.length;
        const batchSize = 1000;
        let hasMore = initialBatch.length === initialBatchSize; // If we got a full batch, there might be more
        let batchCount = 0;
        const batchTimings: number[] = [];
        
        while (hasMore) {
          batchCount++;
          const batchStart = performance.now();
          performance.mark(`${perfId}-batch-${batchCount}-start`);
          console.log(`[${perfId}] Batch ${batchCount}: Starting API call (limit=${batchSize}, offset=${offset})...`);
          
          const batch = await segmentService.listByFlow(filterFlowId, timerange, batchSize, offset);
          
          const batchEnd = performance.now();
          const batchDuration = batchEnd - batchStart;
          batchTimings.push(batchDuration);
          performance.mark(`${perfId}-batch-${batchCount}-end`);
          performance.measure(`${perfId}-batch-${batchCount}`, `${perfId}-batch-${batchCount}-start`, `${perfId}-batch-${batchCount}-end`);
          console.log(`[${perfId}] Batch ${batchCount} completed: ${batchDuration.toFixed(2)}ms, received ${batch.length} segments`);
          
          if (batch.length === 0) {
            hasMore = false;
            console.log(`[${perfId}] No more segments (empty batch)`);
          } else {
            const mergeStart = performance.now();
            allSegments = [...allSegments, ...batch];
            offset += batch.length;
            console.log(`[${perfId}] Merged batch ${batchCount}: ${(performance.now() - mergeStart).toFixed(2)}ms, total segments: ${allSegments.length}`);
            
            const sortPartialStart = performance.now();
            const sortedPartial = sortSegments(allSegments);
            const sortPartialEnd = performance.now();
            console.log(`[${perfId}] Sorting partial (${allSegments.length} segments): ${(sortPartialEnd - sortPartialStart).toFixed(2)}ms`);
            
            const updateStateStart = performance.now();
            setSegments(sortedPartial);
            const updateStateEnd = performance.now();
            console.log(`[${perfId}] State update (setSegments): ${(updateStateEnd - updateStateStart).toFixed(2)}ms`);
            
            // Keep scroll position at the left (first video visible) when new segments are added
            // Use setTimeout to ensure DOM has updated
            const domUpdateStart = performance.now();
            setTimeout(() => {
              const container = document.getElementById('segments-container');
              if (container) {
                // Keep scroll at the left (0) to show first video
                container.scrollLeft = 0;
              }
              console.log(`[${perfId}] DOM update (scroll reset): ${(performance.now() - domUpdateStart).toFixed(2)}ms`);
            }, 0);
            
            // If we got fewer than requested, we've reached the end
            if (batch.length < batchSize) {
              hasMore = false;
              // Set total count when we've loaded everything
              setTotalSegments(allSegments.length);
              console.log(`[${perfId}] Reached end (batch size < ${batchSize})`);
            }
          }
        }
        
        const finalSortStart = performance.now();
        const sortedAll = sortSegments(allSegments);
        const finalSortEnd = performance.now();
        console.log(`[${perfId}] Final sort (${allSegments.length} segments): ${(finalSortEnd - finalSortStart).toFixed(2)}ms`);
        
        const finalStateStart = performance.now();
        setSegments(sortedAll);
        setTotalSegments(sortedAll.length);
        setLoadingMore(false);
        const finalStateEnd = performance.now();
        console.log(`[${perfId}] Final state update: ${(finalStateEnd - finalStateStart).toFixed(2)}ms`);
        
        const backgroundEnd = performance.now();
        const backgroundDuration = backgroundEnd - backgroundStart;
        console.log(`[${perfId}] Background loading completed: ${backgroundDuration.toFixed(2)}ms`);
        console.log(`[${perfId}] Batch timings: ${batchTimings.map(t => t.toFixed(2)).join(', ')}ms`);
        console.log(`[${perfId}] Average batch time: ${(batchTimings.reduce((a, b) => a + b, 0) / batchTimings.length).toFixed(2)}ms`);
      } else {
        // No segments found
        setTotalSegments(0);
        setEstimatedTotal(0);
        setLoadingMore(false);
        console.log(`[${perfId}] No segments found`);
      }
      
      const totalEnd = performance.now();
      const totalDuration = totalEnd - perfStartTime;
      performance.mark(`${perfId}-end`);
      performance.measure(`${perfId}-total`, `${perfId}-start`, `${perfId}-end`);
      console.timeEnd(`${perfId}-total`);
      console.log(`[${perfId}] ✅ Total time: ${totalDuration.toFixed(2)}ms`);
      console.groupEnd();
      
    } catch (error) {
      const errorTime = performance.now();
      const errorDuration = errorTime - perfStartTime;
      console.error(`[${perfId}] ❌ Failed to load segments after ${errorDuration.toFixed(2)}ms:`, error);
      console.groupEnd();
      setSegments([]);
      setLoading(false);
      setLoadingMore(false);
      setTotalSegments(null);
    }
  }, [filterFlowId, startTime, endTime, sortSegments, buildTimerange]);

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
      loadFlowDetails();
      loadSegments();
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
        <Paper sx={{ p: 1.5, mb: 2, backgroundColor: '#e8e8e8' }}>
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
        <Paper sx={{ p: 1.5, mb: 2, backgroundColor: '#e8e8e8' }}>
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

      {/* Loading Page - Show before segments load */}
      {loading ? (
        <Box 
          sx={{ 
            display: 'flex', 
            flexDirection: 'column',
            justifyContent: 'center', 
            alignItems: 'center', 
            minHeight: '60vh',
            p: 4
          }}
        >
          <CircularProgress size={60} thickness={4} />
          <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
            Loading Segments
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', maxWidth: 400 }}>
            {filterFlowId 
              ? `Loading segments for flow: ${filterFlowId}`
              : 'Preparing to load segments...'}
          </Typography>
          {filteredFlow && (
            <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
              <Chip label={filteredFlow.format || 'Unknown'} size="small" />
              {filteredFlow.label && (
                <Chip label={filteredFlow.label} size="small" variant="outlined" />
              )}
            </Box>
          )}
        </Box>
      ) : segments.length === 0 && !loadingMore ? (
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
          {/* Segments Section - Show scroll bar immediately */}
          {(segments.length > 0 || loadingMore) && (
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
                <Typography variant="subtitle1" color="text.secondary">
                  {totalSegments !== null 
                    ? `${segments.length} of ${totalSegments} segment${totalSegments !== 1 ? 's' : ''} loaded`
                    : `${segments.length} segment${segments.length !== 1 ? 's' : ''}${loadingMore ? ' (loading...)' : ''}`
                  }
                </Typography>
                {loadingMore && (
                  <Box sx={{ width: '100%', maxWidth: 300, position: 'relative' }}>
                    <LinearProgress 
                      variant={totalSegments !== null ? "determinate" : "indeterminate"}
                      value={totalSegments !== null ? (segments.length / totalSegments) * 100 : undefined}
                      sx={{ width: '100%' }}
                    />
                    {totalSegments !== null && (
                      <Typography 
                        variant="caption" 
                        color="text.secondary" 
                        sx={{ 
                          mt: 0.5, 
                          display: 'block', 
                          textAlign: 'center',
                          fontWeight: 'medium'
                        }}
                      >
                        {segments.length} of {totalSegments} loaded ({Math.round((segments.length / totalSegments) * 100)}%)
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'row', // Left to right layout
              overflowX: 'auto',
              overflowY: 'hidden',
              pb: 2,
              gap: 0,
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
                flow={filteredFlow}
                width={280}
                height={157.5} // 16:9 aspect ratio
                isFirst={index === 0} // Pass flag to indicate first video
              />
            ))}
          </Box>
            </Box>
          )}

        </Box>
      )}
    </Container>
  );
};

export default Segments;
