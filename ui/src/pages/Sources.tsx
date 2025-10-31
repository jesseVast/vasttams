import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  TableCell,
  CircularProgress,
  Link,
} from '@mui/material';
import { Source } from '../types';
import { sourceService, analyticsService } from '../services/api';
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

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      setLoading(true);
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
    }
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

  const handleOpenDetail = (source: Source) => {
    setSelectedSource(source);
    setDetailModalOpen(true);
  };

  const renderRow = (source: Source, index: number) => {
    // Get flow count and segment count from analytics
    const flowCount = flowCounts[source.id] !== undefined 
      ? flowCounts[source.id] 
      : loading ? '...' : '-';
    const segmentCount = segmentCounts[source.id] !== undefined 
      ? segmentCounts[source.id] 
      : loading ? '...' : '-';
    
    return (
      <>
        <TableCell>
          <Link
            component="button"
            variant="body2"
            onClick={() => handleOpenDetail(source)}
            sx={{ cursor: 'pointer' }}
          >
            Detail
          </Link>
        </TableCell>
        <TableCell>{source.label || '-'}</TableCell>
        <TableCell>{source.description || '-'}</TableCell>
        <TableCell>{source.format}</TableCell>
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
    </Container>
  );
};

export default Sources;

