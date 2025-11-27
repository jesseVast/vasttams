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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoIcon from '@mui/icons-material/Info';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';
import { Flow, Source } from '../types';
import { flowService, sourceService, analyticsService, authService } from '../services/api';
import DataTable, { Column } from '../components/DataTable';
import DetailModal from '../components/DetailModal';
import EditFlowModal from '../components/EditFlowModal';

type SortableField = 'label' | 'format' | 'created';

// Helper function to get last part of format after ":"
const getShortFormat = (format: string | undefined): string => {
  if (!format) return '-';
  const parts = format.split(':');
  return parts.length > 1 ? parts[parts.length - 1] : format;
};

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
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [flowToEdit, setFlowToEdit] = useState<Flow | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [flowToDelete, setFlowToDelete] = useState<Flow | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('');
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
    { id: 'actions', label: 'Actions', sortable: false },
    { id: 'label', label: 'Label', sortable: true },
    { id: 'description', label: 'Description', sortable: false },
    { id: 'format', label: 'Format', sortable: true },
    { id: 'codec', label: 'Codec', sortable: false },
    { id: 'container', label: 'Container', sortable: false },
    { id: 'resolution', label: 'Resolution', sortable: false },
    { id: 'tags', label: 'Tags', sortable: false },
    { id: 'segments', label: 'Segments', sortable: false, align: 'right' },
    { id: 'duration', label: 'Total Time', sortable: false },
    { id: 'created', label: 'Created (Date/Time)', sortable: true },
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

  const handleOpenEdit = async (flow: Flow) => {
    // Prevent viewers from editing
    const user = authService.getCurrentUser();
    if (user?.role === 'viewer') {
      console.warn('Viewers cannot edit flows');
      return;
    }
    
    // Fetch full flow data for editing
    try {
      const fullFlow = await flowService.get(flow.id);
      setFlowToEdit(fullFlow);
      setEditModalOpen(true);
    } catch (error) {
      console.error('Failed to load flow for editing:', error);
      // Fallback to list data if fetch fails
      setFlowToEdit(flow);
      setEditModalOpen(true);
    }
  };

  const handleEditSave = () => {
    // Reload flows after successful edit
    loadFlows();
  };

  const handleOpenDelete = (flow: Flow) => {
    // Prevent viewers from deleting
    const user = authService.getCurrentUser();
    if (user?.role === 'viewer') {
      console.warn('Viewers cannot delete flows');
      return;
    }
    
    setFlowToDelete(flow);
    setDeleteDialogOpen(true);
    setDeleteError(null);
    setDeleteConfirmationText('');
  };

  const handleDeleteConfirm = async () => {
    if (!flowToDelete) return;
    
    // Prevent viewers from deleting
    const user = authService.getCurrentUser();
    if (user?.role === 'viewer') {
      console.warn('Viewers cannot delete flows');
      setDeleteError('Viewers do not have permission to delete flows');
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      // Delete with cascade=true to delete segments and clean up S3 objects
      const result = await flowService.delete(flowToDelete.id, true);
      
      // Handle 202 Accepted (background deletion) or 200 OK (immediate deletion)
      if (result.status === 202 || result.status === 200) {
        setDeleteDialogOpen(false);
        setFlowToDelete(null);
        // Reload flows after successful deletion (with small delay for 202 to allow background task to start)
        setTimeout(() => {
          loadFlows();
        }, 500);
      }
    } catch (error: any) {
      console.error('Failed to delete flow:', error);
      setDeleteError(
        error.response?.data?.detail || 
        error.message || 
        'Failed to delete flow. It may be read-only or have dependencies that prevent deletion.'
      );
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setFlowToDelete(null);
    setDeleteError(null);
    setDeleteConfirmationText('');
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
    
    // Check if user is viewer (should not see edit/delete options)
    const user = authService.getCurrentUser();
    const isViewer = user?.role === 'viewer';
    
    return (
    <>
        <TableCell>
          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
            <Tooltip title="View Details">
              <IconButton
                size="small"
                onClick={() => handleOpenDetail(flow)}
                sx={{ padding: '4px' }}
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            {!isViewer && (
              <Tooltip title="Edit Flow">
                <IconButton
                  size="small"
                  onClick={() => handleOpenEdit(flow)}
                  sx={{ padding: '4px' }}
                >
                  <EditIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title="View Segments">
              <IconButton
                size="small"
                onClick={() => navigate(`/segments?flow_id=${flow.id}`)}
                sx={{ padding: '4px' }}
              >
                <PlayArrowIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            {!isViewer && (
              <Tooltip title="Delete Flow">
                <IconButton
                  size="small"
                  onClick={() => handleOpenDelete(flow)}
                  sx={{ padding: '4px', color: 'error.main' }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </TableCell>
      <TableCell>{flow.label || '-'}</TableCell>
      <TableCell>{flow.description || '-'}</TableCell>
      <TableCell>{getShortFormat(flow.format)}</TableCell>
      <TableCell>{flow.codec || '-'}</TableCell>
      <TableCell>{flow.container || '-'}</TableCell>
      <TableCell>
        {flow.essence_parameters?.frame_width && flow.essence_parameters?.frame_height
          ? `${flow.essence_parameters.frame_width}x${flow.essence_parameters.frame_height}`
          : '-'}
      </TableCell>
      <TableCell>
        {(() => {
          // Handle tags that might be nested under 'root' or at top level
          const tags = flow.tags;
          if (!tags) return <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>-</Typography>;
          
          // Check if tags has a 'root' property with content
          const tagsToDisplay = tags.root && typeof tags.root === 'object' 
            ? tags.root 
            : tags;
          
          // Filter to only show 'type' and 'sport' tags
          const allowedTags = ['type', 'sport'];
          const filteredTags = tagsToDisplay && typeof tagsToDisplay === 'object'
            ? Object.entries(tagsToDisplay).filter(([key]) => allowedTags.includes(key))
            : [];
          
          if (filteredTags.length === 0) {
            return <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>-</Typography>;
          }
          
          // Display filtered tags as chips with values
          return (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxWidth: 300 }}>
              {filteredTags.map(([key, value]) => {
                const displayValue = Array.isArray(value) 
                  ? value.join(', ')
                  : String(value);
                const chipLabel = `${key}: ${displayValue}`;
                return (
                  <Tooltip key={key} title={chipLabel} arrow>
                    <Chip
                      label={chipLabel}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem', height: 24 }}
                    />
                  </Tooltip>
                );
              })}
            </Box>
          );
        })()}
      </TableCell>
        <TableCell align="right">
          {typeof segmentCount === 'number' ? segmentCount.toLocaleString() : segmentCount}
        </TableCell>
        <TableCell>{formattedDuration}</TableCell>
      <TableCell>{flow.created ? new Date(flow.created).toLocaleString() : '-'}</TableCell>
    </>
  );
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
    <Container>
      {/* Compact Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Flows
          </Typography>
          <Tooltip title="Refresh flows">
            <IconButton 
              onClick={handleRefresh} 
              disabled={loading || refreshing}
              size="small"
              aria-label="refresh flows"
            >
              <RefreshIcon sx={{ 
                fontSize: 18,
                animation: refreshing ? 'spin 1s linear infinite' : 'none',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' }
                }
              }} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Compact Filter Section */}
      <Box sx={{ mb: 1.5 }}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1,
            alignItems: 'center',
            '& > *': {
              flex: { xs: '1 1 100%', sm: '0 1 auto' },
              minWidth: { xs: '100%', sm: 'auto' },
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
                sx: { width: 160 },
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
                sx: { width: 160 },
              },
            }}
          />
          <TextField
            label="Source ID"
            value={filterSourceId}
            onChange={(e) => setFilterSourceId(e.target.value)}
            placeholder="Source ID"
            size="small"
            sx={{ width: 160 }}
          />
          <FormControl size="small" sx={{ width: 130 }}>
            <InputLabel>Codec</InputLabel>
            <Select
              value={filterCodec}
              label="Codec"
              onChange={(e) => setFilterCodec(e.target.value)}
            >
              <MenuItem value="">
                <em>All</em>
              </MenuItem>
              {uniqueCodecs.map(codec => (
                <MenuItem key={codec} value={codec}>{codec}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ width: 130 }}>
            <InputLabel>Resolution</InputLabel>
            <Select
              value={filterResolution}
              label="Resolution"
              onChange={(e) => setFilterResolution(e.target.value)}
            >
              <MenuItem value="">
                <em>All</em>
              </MenuItem>
              {uniqueResolutions.map(resolution => (
                <MenuItem key={resolution} value={resolution}>{resolution}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ width: 130 }}>
            <InputLabel>Frame Rate</InputLabel>
            <Select
              value={filterFrameRate}
              label="Frame Rate"
              onChange={(e) => setFilterFrameRate(e.target.value)}
            >
              <MenuItem value="">
                <em>All</em>
              </MenuItem>
              {uniqueFrameRates.map(frameRate => (
                <MenuItem key={frameRate} value={frameRate}>{frameRate}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<SearchIcon />}
            onClick={() => {
              // Filters are applied automatically via useMemo, but we can trigger a visual feedback
              // The search button serves as a visual indicator
            }}
            size="small"
            sx={{
              minWidth: 100,
            }}
          >
            Search
          </Button>
        </Box>
      </Box>

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
      
      <EditFlowModal
        open={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setFlowToEdit(null);
        }}
        flow={flowToEdit}
        onSave={handleEditSave}
      />

      <Dialog
        open={deleteDialogOpen}
        onClose={(event, reason) => {
          // Prevent closing by clicking outside or pressing escape
          if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
            return;
          }
          handleDeleteCancel();
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Delete Flow</DialogTitle>
        <DialogContent>
          {deleteError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {deleteError}
            </Alert>
          )}
          <DialogContentText>
            Are you sure you want to delete this flow? This action will:
          </DialogContentText>
          <Box component="ul" sx={{ mt: 1, mb: 2, pl: 3 }}>
            <li>Delete the flow</li>
            <li>Delete all associated segments</li>
            <li>Delete all S3 objects referenced by those segments</li>
          </Box>
          {flowToDelete && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Flow Details:
              </Typography>
              <Typography variant="body2">
                <strong>ID:</strong> {flowToDelete.id}
              </Typography>
              {flowToDelete.label && (
                <Typography variant="body2">
                  <strong>Label:</strong> {flowToDelete.label}
                </Typography>
              )}
              <Typography variant="body2">
                <strong>Format:</strong> {getShortFormat(flowToDelete.format)}
              </Typography>
              {flowToDelete.codec && (
                <Typography variant="body2">
                  <strong>Codec:</strong> {flowToDelete.codec}
                </Typography>
              )}
              {flowToDelete.container && (
                <Typography variant="body2">
                  <strong>Container:</strong> {flowToDelete.container}
                </Typography>
              )}
              {segmentCounts[flowToDelete.id] !== undefined && (
                <Typography variant="body2">
                  <strong>Segments:</strong> {segmentCounts[flowToDelete.id]}
                </Typography>
              )}
            </Box>
          )}
          <DialogContentText sx={{ mt: 2, fontWeight: 'bold', color: 'error.main' }}>
            This action cannot be undone!
          </DialogContentText>
          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 'bold' }}>
              Type <strong>DELETE</strong> to confirm:
            </Typography>
            <TextField
              fullWidth
              size="small"
              value={deleteConfirmationText}
              onChange={(e) => setDeleteConfirmationText(e.target.value)}
              placeholder="DELETE"
              disabled={deleting}
              error={deleteConfirmationText !== '' && deleteConfirmationText !== 'DELETE'}
              helperText={
                deleteConfirmationText !== '' && deleteConfirmationText !== 'DELETE'
                  ? 'Please type DELETE exactly to confirm'
                  : ''
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={deleting || deleteConfirmationText !== 'DELETE'}
            startIcon={deleting ? <CircularProgress size={16} /> : null}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
    </LocalizationProvider>
  );
};

export default Flows;

