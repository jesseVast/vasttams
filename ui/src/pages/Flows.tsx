import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Typography,
  TableCell,
  CircularProgress,
  Box,
  TextField,
  Chip,
  Card,
  CardContent,
  Link,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';
import { Flow, Source } from '../types';
import { flowService, sourceService, analyticsService } from '../services/api';
import DataTable, { Column } from '../components/DataTable';
import DetailModal from '../components/DetailModal';

type SortableField = 'label' | 'format' | 'source_id' | 'created';

const Flows: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [flows, setFlows] = useState<Flow[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [filterSourceId, setFilterSourceId] = useState<string>(searchParams.get('source_id') || '');
  const [filterCodec, setFilterCodec] = useState<string>('');
  const [filterResolution, setFilterResolution] = useState<string>('');
  const [filterFrameRate, setFilterFrameRate] = useState<string>('');
  const [filterDateFrom, setFilterDateFrom] = useState<Dayjs | null>(null);
  const [filterDateTo, setFilterDateTo] = useState<Dayjs | null>(null);
  const [loading, setLoading] = useState(true);
  const [filteredSource, setFilteredSource] = useState<Source | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState<SortableField>('created');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [segmentCounts, setSegmentCounts] = useState<Record<string, number>>({});
  const [flowDurations, setFlowDurations] = useState<Record<string, number>>({});
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedFlow, setSelectedFlow] = useState<Flow | null>(null);
  // Filter values loaded independently for dropdowns
  const [uniqueCodecsForFilters, setUniqueCodecsForFilters] = useState<string[]>([]);
  const [uniqueResolutionsForFilters, setUniqueResolutionsForFilters] = useState<string[]>([]);
  const [uniqueFrameRatesForFilters, setUniqueFrameRatesForFilters] = useState<string[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadSources();
    loadFlows(); // Load flows - filter values will be extracted immediately
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Update URL when filter changes
    if (filterSourceId) {
      setSearchParams({ source_id: filterSourceId }, { replace: true });
      // Find the source details
      const source = sources.find(s => s.id === filterSourceId);
      setFilteredSource(source || null);
    } else {
      setSearchParams({}, { replace: true });
      setFilteredSource(null);
    }
  }, [filterSourceId, setSearchParams, sources]);

  const loadSources = async () => {
    try {
      const data = await sourceService.list();
      setSources(data);
    } catch (error) {
      console.error('Failed to load sources:', error);
    }
  };

  // Extract filter values from flows immediately when they load
  const extractFilterValues = (flowsData: Flow[]) => {
    const codecs = new Set<string>();
    const resolutions = new Set<string>();
    const frameRates = new Set<string>();
    
    flowsData.forEach(flow => {
      if (flow.codec) {
        codecs.add(flow.codec);
      }
      if (flow.essence_parameters?.frame_width && flow.essence_parameters?.frame_height) {
        const resolution = `${flow.essence_parameters.frame_width}x${flow.essence_parameters.frame_height}`;
        resolutions.add(resolution);
      }
      if (flow.essence_parameters?.frame_rate) {
        const fr = flow.essence_parameters.frame_rate;
        const frameRateStr = fr.value || 
          (fr.numerator && fr.denominator ? `${fr.numerator}/${fr.denominator}` : '');
        if (frameRateStr) {
          frameRates.add(frameRateStr);
        }
      }
    });
    
    // Set filter values immediately so dropdowns are populated right away
    setUniqueCodecsForFilters(Array.from(codecs).sort());
    setUniqueResolutionsForFilters(Array.from(resolutions).sort((a, b) => {
      const [aWidth, aHeight] = a.split('x').map(Number);
      const [bWidth, bHeight] = b.split('x').map(Number);
      if (aWidth !== bWidth) return aWidth - bWidth;
      return aHeight - bHeight;
    }));
    setUniqueFrameRatesForFilters(Array.from(frameRates).sort((a, b) => {
      const aNum = parseFloat(a);
      const bNum = parseFloat(b);
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      if (a.includes('/') && b.includes('/')) {
        const [aNum, aDen] = a.split('/').map(Number);
        const [bNum, bDen] = b.split('/').map(Number);
        const aVal = aNum / aDen;
        const bVal = bNum / bDen;
        return aVal - bVal;
      }
      return a.localeCompare(b);
    }));
  };

  // Format duration in human-readable format
  const formatDuration = (seconds: number | null): string => {
    if (seconds === null || seconds === 0) return '-';
    
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = (seconds % 60).toFixed(0);
      return `${mins}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${mins}m`;
    }
  };

  const loadFlows = async () => {
    try {
      if (!refreshing) {
        setLoading(true);
      }
      // Load flows list first - extract filter values immediately
      const flowsData = await flowService.list();
      
      // Extract filter values immediately so dropdowns are populated right away
      extractFilterValues(flowsData);
      
      // Set flows immediately so UI can start rendering
      setFlows(flowsData);
      
      // Load analytics in parallel (non-blocking for filter dropdowns)
      analyticsService.getFlowAnalytics()
        .then(analyticsData => {
          // Extract segment counts and durations from analytics
          const counts: Record<string, number> = {};
          const durations: Record<string, number> = {};
          
          analyticsData.forEach((analytics) => {
            if (analytics.flow_id) {
              counts[analytics.flow_id] = analytics.segment_count || 0;
              if (analytics.total_duration_seconds !== null && analytics.total_duration_seconds !== undefined) {
                durations[analytics.flow_id] = analytics.total_duration_seconds;
              }
            }
          });
          
          setSegmentCounts(counts);
          setFlowDurations(durations);
        })
        .catch(error => {
          console.error('Failed to load analytics:', error);
        });
    } catch (error) {
      console.error('Failed to load flows:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadFlows();
    loadSources(); // Also refresh sources list
  };

  // Extract unique values for dropdowns - merge with pre-loaded filter values
  const uniqueCodecs = useMemo(() => {
    const codecs = new Set<string>(uniqueCodecsForFilters); // Start with pre-loaded values
    flows.forEach(flow => {
      if (flow.codec) {
        codecs.add(flow.codec);
      }
    });
    return Array.from(codecs).sort();
  }, [flows, uniqueCodecsForFilters]);

  const uniqueResolutions = useMemo(() => {
    const resolutions = new Set<string>(uniqueResolutionsForFilters); // Start with pre-loaded values
    flows.forEach(flow => {
      if (flow.essence_parameters?.frame_width && flow.essence_parameters?.frame_height) {
        const resolution = `${flow.essence_parameters.frame_width}x${flow.essence_parameters.frame_height}`;
        resolutions.add(resolution);
      }
    });
    return Array.from(resolutions).sort((a, b) => {
      const [aWidth, aHeight] = a.split('x').map(Number);
      const [bWidth, bHeight] = b.split('x').map(Number);
      if (aWidth !== bWidth) return aWidth - bWidth;
      return aHeight - bHeight;
    });
  }, [flows, uniqueResolutionsForFilters]);

  const uniqueFrameRates = useMemo(() => {
    const frameRates = new Set<string>(uniqueFrameRatesForFilters); // Start with pre-loaded values
    flows.forEach(flow => {
      if (flow.essence_parameters?.frame_rate) {
        const fr = flow.essence_parameters.frame_rate;
        const frameRateStr = fr.value || 
          (fr.numerator && fr.denominator ? `${fr.numerator}/${fr.denominator}` : '');
        if (frameRateStr) {
          frameRates.add(frameRateStr);
        }
      }
    });
    return Array.from(frameRates).sort((a, b) => {
      // Try to sort numerically if possible
      const aNum = parseFloat(a);
      const bNum = parseFloat(b);
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      // For fractional, calculate value
      if (a.includes('/') && b.includes('/')) {
        const [aNum, aDen] = a.split('/').map(Number);
        const [bNum, bDen] = b.split('/').map(Number);
        const aVal = aNum / aDen;
        const bVal = bNum / bDen;
        return aVal - bVal;
      }
      return a.localeCompare(b);
    });
  }, [flows, uniqueFrameRatesForFilters]);

  const handleSort = (property: string | keyof Flow) => {
    const sortField = property as SortableField;
    const isAsc = orderBy === sortField && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(sortField);
  };

  // Apply all filters
  const filteredFlows = useMemo(() => {
    return flows.filter(flow => {
      // Source ID filter
      if (filterSourceId && flow.source_id !== filterSourceId) {
        return false;
      }
      
      // Codec filter
      if (filterCodec && flow.codec !== filterCodec) {
        return false;
      }
      
      // Resolution filter
      if (filterResolution) {
        const flowResolution = flow.essence_parameters?.frame_width && flow.essence_parameters?.frame_height
          ? `${flow.essence_parameters.frame_width}x${flow.essence_parameters.frame_height}`
          : '';
        if (flowResolution !== filterResolution) {
          return false;
        }
      }
      
      // Frame rate filter
      if (filterFrameRate) {
        const fr = flow.essence_parameters?.frame_rate;
        const flowFrameRate = fr?.value || 
          (fr?.numerator && fr?.denominator ? `${fr.numerator}/${fr.denominator}` : '');
        if (flowFrameRate !== filterFrameRate) {
          return false;
        }
      }
      
      // Date range filter
      if (flow.created) {
        const flowDate = dayjs(flow.created);
        
        if (filterDateFrom && flowDate.isBefore(filterDateFrom)) {
          return false;
        }
        
        if (filterDateTo && flowDate.isAfter(filterDateTo)) {
          return false;
        }
      } else if (filterDateFrom || filterDateTo) {
        // If date filters are set but flow has no created date, exclude it
        return false;
      }
      
      return true;
    });
  }, [flows, filterSourceId, filterCodec, filterResolution, filterFrameRate, filterDateFrom, filterDateTo]);

  // Sort filtered flows
  const sortedFlows = useMemo(() => {
    return [...filteredFlows].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'label':
          aValue = a.label || '';
          bValue = b.label || '';
          break;
        case 'format':
          aValue = a.format || '';
          bValue = b.format || '';
          break;
        case 'source_id':
          aValue = a.source_id || '';
          bValue = b.source_id || '';
          break;
        case 'created':
          aValue = a.created ? new Date(a.created).getTime() : 0;
          bValue = b.created ? new Date(b.created).getTime() : 0;
          break;
        default:
          return 0;
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return order === 'asc' ? aValue - bValue : bValue - aValue;
      } else {
        const aStr = String(aValue);
        const bStr = String(bValue);
        return order === 'asc' 
          ? aStr.localeCompare(bStr)
          : bStr.localeCompare(aStr);
      }
    });
  }, [filteredFlows, orderBy, order]);

  // Paginate sorted flows
  const paginatedFlows = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedFlows.slice(start, start + rowsPerPage);
  }, [sortedFlows, page, rowsPerPage]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const columns: Column<Flow>[] = [
    { id: 'detail', label: 'Detail', sortable: false },
    { id: 'label', label: 'Label', sortable: true },
    { id: 'description', label: 'Description', sortable: false },
    { id: 'format', label: 'Format', sortable: true },
    { id: 'source_id', label: 'Source ID', sortable: true },
    { id: 'segments', label: 'Segments', sortable: false, align: 'right' },
    { id: 'duration', label: 'Total Time', sortable: false },
    { id: 'created', label: 'Created (Date/Time)', sortable: true },
    { id: 'actions', label: 'Actions', sortable: false },
  ];

  const handleOpenDetail = async (flow: Flow) => {
    // Fetch full flow data to get flow_collection computed on-demand
    try {
      const fullFlow = await flowService.get(flow.id);
      setSelectedFlow(fullFlow);
      setDetailModalOpen(true);
    } catch (error) {
      console.error('Failed to load flow details:', error);
      // Fallback to list data if fetch fails
      setSelectedFlow(flow);
      setDetailModalOpen(true);
    }
  };

  const renderRow = (flow: Flow, index: number) => {
    // Get segment count - show "Loading..." if still loading
    const segmentCount = segmentCounts[flow.id] !== undefined 
      ? segmentCounts[flow.id] 
      : loading ? '...' : '-';
    
    // Get duration calculated from segments
    const duration = flowDurations[flow.id] !== undefined 
      ? flowDurations[flow.id] 
      : null;
    const formattedDuration = formatDuration(duration);
    
    return (
    <>
        <TableCell>
          <Link
            component="button"
            variant="body2"
            onClick={() => handleOpenDetail(flow)}
            sx={{ cursor: 'pointer' }}
          >
            Detail
          </Link>
        </TableCell>
      <TableCell>{flow.label || '-'}</TableCell>
      <TableCell>{flow.description || '-'}</TableCell>
      <TableCell>{flow.format}</TableCell>
      <TableCell>{flow.source_id}</TableCell>
        <TableCell align="right">
          {typeof segmentCount === 'number' ? segmentCount.toLocaleString() : segmentCount}
        </TableCell>
        <TableCell>{formattedDuration}</TableCell>
      <TableCell>{flow.created ? new Date(flow.created).toLocaleString() : '-'}</TableCell>
      <TableCell>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate(`/segments?flow_id=${flow.id}`)}
          sx={{ cursor: 'pointer' }}
        >
          View Segments
        </Link>
      </TableCell>
    </>
  );
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Flows
        </Typography>
        <Tooltip title="Refresh flows">
          <IconButton 
            onClick={handleRefresh} 
            disabled={loading || refreshing}
            color="primary"
            aria-label="refresh flows"
          >
            <RefreshIcon sx={{ 
              animation: refreshing ? 'spin 1s linear infinite' : 'none',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' }
              }
            }} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Filter Section */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
          Filters:
        </Typography>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1.5,
            alignItems: 'flex-end',
            '& > *': {
              flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 6px)', md: '0 1 auto' },
              minWidth: { xs: '100%', sm: '150px', md: 'auto' },
            },
          }}
        >
          <DateTimePicker
            label="Date From"
            value={filterDateFrom}
            onChange={(newValue) => setFilterDateFrom(newValue)}
            slotProps={{
              textField: {
                size: 'small',
                sx: { width: 180 },
              },
            }}
          />
          <DateTimePicker
            label="Date To"
            value={filterDateTo}
            onChange={(newValue) => setFilterDateTo(newValue)}
            slotProps={{
              textField: {
                size: 'small',
                sx: { width: 180 },
              },
            }}
          />
          <TextField
            label="Filter by Source ID"
            value={filterSourceId}
            onChange={(e) => setFilterSourceId(e.target.value)}
            placeholder="Enter source ID"
            size="small"
            sx={{ minWidth: 200 }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Codec</InputLabel>
            <Select
              value={filterCodec}
              label="Codec"
              onChange={(e) => setFilterCodec(e.target.value)}
            >
              <MenuItem value="">
                <em>All Codecs</em>
              </MenuItem>
              {uniqueCodecs.map(codec => (
                <MenuItem key={codec} value={codec}>{codec}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Resolution</InputLabel>
            <Select
              value={filterResolution}
              label="Resolution"
              onChange={(e) => setFilterResolution(e.target.value)}
            >
              <MenuItem value="">
                <em>All Resolutions</em>
              </MenuItem>
              {uniqueResolutions.map(resolution => (
                <MenuItem key={resolution} value={resolution}>{resolution}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Frame Rate</InputLabel>
            <Select
              value={filterFrameRate}
              label="Frame Rate"
              onChange={(e) => setFilterFrameRate(e.target.value)}
            >
              <MenuItem value="">
                <em>All Frame Rates</em>
              </MenuItem>
              {uniqueFrameRates.map(frameRate => (
                <MenuItem key={frameRate} value={frameRate}>{frameRate}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={() => {
              // Filters are applied automatically via useMemo, but we can trigger a visual feedback
              // The search button serves as a visual indicator
            }}
            sx={{
              minWidth: 120,
              height: 40,
            }}
          >
            Search
          </Button>
        </Box>
      </Box>

      {filteredSource && (
        <Card sx={{ mb: 2, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Source Information:
              </Typography>
              
              {/* Basic Info */}
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                  Basic Information:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip label={`ID: ${filteredSource.id}`} size="small" variant="outlined" />
                  {filteredSource.label && (
                    <Chip label={`Label: ${filteredSource.label}`} size="small" variant="outlined" />
                  )}
                  <Chip label={`Format: ${filteredSource.format}`} size="small" variant="outlined" color="primary" />
                </Box>
              </Box>

              {/* Description */}
              {filteredSource.description && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Description:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {filteredSource.description}
                  </Typography>
                </Box>
              )}

              {/* Source Collection */}
              {filteredSource.source_collection && filteredSource.source_collection.length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Source Collection:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {filteredSource.source_collection.map((item, index) => (
                      <Chip
                        key={index}
                        label={item.label || item.id}
                        size="small"
                        variant="outlined"
                        color="secondary"
                      />
                    ))}
                  </Box>
                </Box>
              )}

              {/* Collected By */}
              {filteredSource.collected_by && filteredSource.collected_by.length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Collected By:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {filteredSource.collected_by.map((sourceId, index) => (
                      <Chip
                        key={index}
                        label={sourceId}
                        size="small"
                        variant="outlined"
                        color="info"
                      />
                    ))}
                  </Box>
                </Box>
              )}

              {/* Metadata */}
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {filteredSource.created_by && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Created by:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {filteredSource.created_by}
                    </Typography>
                  </Box>
                )}
                {filteredSource.updated_by && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Updated by:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {filteredSource.updated_by}
                    </Typography>
                  </Box>
                )}
                {filteredSource.created && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Created:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(filteredSource.created).toLocaleString()}
                    </Typography>
                  </Box>
                )}
                {filteredSource.updated && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Updated:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(filteredSource.updated).toLocaleString()}
                    </Typography>
                  </Box>
                )}
              </Box>

              {/* Tags */}
              {filteredSource.tags && Object.keys(filteredSource.tags).length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Tags:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {Object.entries(filteredSource.tags).map(([key, value]) => (
                      <Chip 
                        key={key} 
                        label={`${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`} 
                        size="small" 
                        variant="outlined"
                        color="primary"
                      />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading flows...</Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedFlows}
          getRowId={(flow) => flow.id}
          renderRow={renderRow}
          page={page}
          rowsPerPage={rowsPerPage}
          totalCount={filteredFlows.length}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          orderBy={orderBy}
          order={order}
          onSort={handleSort}
        />
      )}
      
      <DetailModal
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        data={selectedFlow}
        title="Flow Details"
      />
    </Container>
    </LocalizationProvider>
  );
};

export default Flows;

