import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  TableCell,
  CircularProgress,
  Link,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Alert,
  TextField,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info';
import { Source } from '../types';
import { sourceService, analyticsService, authService } from '../services/api';
import DataTable, { Column } from '../components/DataTable';
import DetailModal from '../components/DetailModal';

type SortableField = 'label' | 'format' | 'created';

const Sources: React.FC = () => {
  const navigate = useNavigate();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState<SortableField>('created');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [flowCounts, setFlowCounts] = useState<Record<string, number>>({});
  const [segmentCounts, setSegmentCounts] = useState<Record<string, number>>({});
  const [refreshing, setRefreshing] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sourceToDelete, setSourceToDelete] = useState<Source | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('');

  useEffect(() => {
    loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSources = async () => {
    try {
      if (!refreshing) {
        setLoading(true);
      }
      // Load sources and analytics in parallel
      const [sourcesData, analyticsData] = await Promise.all([
        sourceService.list(),
        analyticsService.getSourceAnalytics()
      ]);
      
      setSources(sourcesData);
      
      // Extract flow counts and segment counts from analytics
      const flowCountsMap: Record<string, number> = {};
      const segmentCountsMap: Record<string, number> = {};
      
      analyticsData.forEach((analytics) => {
        if (analytics.source_id) {
          flowCountsMap[analytics.source_id] = analytics.flow_count !== undefined ? analytics.flow_count : 0;
          segmentCountsMap[analytics.source_id] = analytics.segment_count !== undefined ? analytics.segment_count : 0;
        }
      });
      
      // Ensure all sources have entries (even if 0)
      sourcesData.forEach((source) => {
        if (!flowCountsMap.hasOwnProperty(source.id)) {
          flowCountsMap[source.id] = 0;
        }
        if (!segmentCountsMap.hasOwnProperty(source.id)) {
          segmentCountsMap[source.id] = 0;
        }
      });
      
      setFlowCounts(flowCountsMap);
      setSegmentCounts(segmentCountsMap);
    } catch (error) {
      console.error('Failed to load sources:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadSources();
  };

  const handleSort = (property: string | keyof Source) => {
    const sortField = property as SortableField;
    const isAsc = orderBy === sortField && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(sortField);
  };

  const sortedSources = useMemo(() => {
    return [...sources].sort((a, b) => {
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
  }, [sources, orderBy, order]);

  const paginatedSources = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedSources.slice(start, start + rowsPerPage);
  }, [sortedSources, page, rowsPerPage]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const columns: Column<Source>[] = [
    { id: 'detail', label: 'Detail', sortable: false },
    { id: 'label', label: 'Label', sortable: true },
    { id: 'description', label: 'Description', sortable: false },
    { id: 'format', label: 'Format', sortable: true },
    { id: 'flows', label: 'Flows', sortable: false, align: 'right' },
    { id: 'segments', label: 'Segments', sortable: false, align: 'right' },
    { id: 'created', label: 'Created (Date/Time)', sortable: true },
    { id: 'actions', label: 'Actions', sortable: false },
  ];

  const handleOpenDetail = async (source: Source) => {
    // Fetch full source data to get source_collection computed on-demand
    try {
      const fullSource = await sourceService.get(source.id);
      setSelectedSource(fullSource);
      setDetailModalOpen(true);
    } catch (error) {
      console.error('Failed to load source details:', error);
      // Fallback to list data if fetch fails
      setSelectedSource(source);
      setDetailModalOpen(true);
    }
  };

  const handleOpenDelete = (source: Source) => {
    // Prevent viewers from deleting
    const user = authService.getCurrentUser();
    if (user?.role === 'viewer') {
      console.warn('Viewers cannot delete sources');
      return;
    }
    
    setSourceToDelete(source);
    setDeleteDialogOpen(true);
    setDeleteError(null);
    setDeleteConfirmationText('');
  };

  const handleDeleteConfirm = async () => {
    if (!sourceToDelete) return;
    
    // Prevent viewers from deleting
    const user = authService.getCurrentUser();
    if (user?.role === 'viewer') {
      console.warn('Viewers cannot delete sources');
      setDeleteError('Viewers do not have permission to delete sources');
      return;
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      // Delete with cascade=true to delete flows, segments, and S3 objects
      const result = await sourceService.delete(sourceToDelete.id, true);
      
      // Handle 202 Accepted (background deletion) or 200 OK (immediate deletion)
      if (result.status === 202 || result.status === 200) {
        setDeleteDialogOpen(false);
        setSourceToDelete(null);
        // Reload sources after successful deletion (with small delay for 202 to allow background task to start)
        setTimeout(() => {
          loadSources();
        }, 500);
      }
    } catch (error: any) {
      console.error('Failed to delete source:', error);
      setDeleteError(
        error.response?.data?.detail || 
        error.message || 
        'Failed to delete source. It may have dependencies that prevent deletion.'
      );
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setSourceToDelete(null);
    setDeleteError(null);
    setDeleteConfirmationText('');
  };

  const renderRow = (source: Source, index: number) => {
    // Get flow count and segment count from analytics
    const flowCount = flowCounts[source.id] !== undefined 
      ? flowCounts[source.id] 
      : loading ? '...' : '-';
    const segmentCount = segmentCounts[source.id] !== undefined 
      ? segmentCounts[source.id] 
      : loading ? '...' : '-';
    
    // Check if user is viewer (should not see delete option)
    const user = authService.getCurrentUser();
    const isViewer = user?.role === 'viewer';
    
    return (
    <>
        <TableCell>
          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
            <Tooltip title="View Details">
              <IconButton
                size="small"
                onClick={() => handleOpenDetail(source)}
                sx={{ padding: '4px' }}
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            {!isViewer && (
              <Tooltip title="Delete Source">
                <IconButton
                  size="small"
                  onClick={() => handleOpenDelete(source)}
                  sx={{ padding: '4px', color: 'error.main' }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </TableCell>
      <TableCell>{source.label || '-'}</TableCell>
      <TableCell>{source.description || '-'}</TableCell>
      <TableCell>
        {source.format
          ? (source.format.includes(':') 
              ? source.format.split(':').pop() 
              : source.format)
          : '-'}
      </TableCell>
        <TableCell align="right">
          {typeof flowCount === 'number' ? flowCount.toLocaleString() : flowCount}
        </TableCell>
        <TableCell align="right">
          {typeof segmentCount === 'number' ? segmentCount.toLocaleString() : segmentCount}
        </TableCell>
      <TableCell>{source.created ? new Date(source.created).toLocaleString() : '-'}</TableCell>
      <TableCell>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate(`/flows?source_id=${source.id}`)}
          sx={{ cursor: 'pointer' }}
        >
          View Flows
        </Link>
      </TableCell>
    </>
  );
  };

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Sources
        </Typography>
        <Tooltip title="Refresh sources">
          <IconButton 
            onClick={handleRefresh} 
            disabled={loading || refreshing}
            color="primary"
            aria-label="refresh sources"
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

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading sources...</Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedSources}
          getRowId={(source) => source.id}
          renderRow={renderRow}
          page={page}
          rowsPerPage={rowsPerPage}
          totalCount={sources.length}
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
        data={selectedSource}
        title="Source Details"
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
        <DialogTitle>Delete Source</DialogTitle>
        <DialogContent>
          {deleteError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {deleteError}
            </Alert>
          )}
          <DialogContentText>
            Are you sure you want to delete this source? This action will:
          </DialogContentText>
          <Box component="ul" sx={{ mt: 1, mb: 2, pl: 3 }}>
            <li>Delete the source</li>
            <li>Delete all associated flows</li>
            <li>Delete all associated segments</li>
            <li>Delete all S3 objects referenced by those segments</li>
          </Box>
          {sourceToDelete && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Source Details:
              </Typography>
              <Typography variant="body2">
                <strong>ID:</strong> {sourceToDelete.id}
              </Typography>
              {sourceToDelete.label && (
                <Typography variant="body2">
                  <strong>Label:</strong> {sourceToDelete.label}
                </Typography>
              )}
              <Typography variant="body2">
                <strong>Format:</strong> {sourceToDelete.format}
              </Typography>
              {flowCounts[sourceToDelete.id] !== undefined && (
                <Typography variant="body2">
                  <strong>Flows:</strong> {flowCounts[sourceToDelete.id]}
                </Typography>
              )}
              {segmentCounts[sourceToDelete.id] !== undefined && (
                <Typography variant="body2">
                  <strong>Segments:</strong> {segmentCounts[sourceToDelete.id]}
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
  );
};

export default Sources;

