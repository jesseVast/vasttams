import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container,
  Typography,
  TableCell,
  TextField,
  CircularProgress,
  Box,
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import { Segment, Flow } from '../types';
import { segmentService, flowService } from '../services/api';
import DataTable, { Column } from '../components/DataTable';

type SortableField = 'object_id' | 'timerange' | 'sample_offset' | 'sample_count' | 'key_frame_count';

const Segments: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [filterFlowId, setFilterFlowId] = useState<string>(searchParams.get('flow_id') || '');
  const [loading, setLoading] = useState(false);
  const [filteredFlow, setFilteredFlow] = useState<Flow | null>(null);
  const [orderBy, setOrderBy] = useState<SortableField>('sample_offset');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

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
      // Find the flow details
      loadFlowDetails();
      // Load segments
      loadSegments();
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

  const loadSegments = async () => {
    if (!filterFlowId) return;
    
    try {
      setLoading(true);
      const data = await segmentService.listByFlow(filterFlowId);
      setSegments(data);
    } catch (error) {
      console.error('Failed to load segments:', error);
      setSegments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (property: string | keyof Segment) => {
    const sortField = property as SortableField;
    const isAsc = orderBy === sortField && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(sortField);
  };

  const sortedSegments = useMemo(() => {
    return [...segments].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'object_id':
          aValue = a.object_id || '';
          bValue = b.object_id || '';
          break;
        case 'timerange':
          aValue = a.timerange?.value || '';
          bValue = b.timerange?.value || '';
          break;
        case 'sample_offset':
          aValue = a.sample_offset ?? -1;
          bValue = b.sample_offset ?? -1;
          break;
        case 'sample_count':
          aValue = a.sample_count ?? -1;
          bValue = b.sample_count ?? -1;
          break;
        case 'key_frame_count':
          aValue = a.key_frame_count ?? -1;
          bValue = b.key_frame_count ?? -1;
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
  }, [segments, orderBy, order]);

  const getFirstPresignedUrl = (segment: Segment) => {
    return segment.get_urls?.find(url => url.presigned && url.url) || segment.get_urls?.[0];
  };

  const getVideoMimeType = (url: string): string => {
    // Extract file extension from URL
    const urlLower = url.toLowerCase();
    if (urlLower.includes('.ts') || urlLower.endsWith('.ts')) {
      return 'video/mp2t'; // MPEG Transport Stream
    } else if (urlLower.includes('.mp4') || urlLower.endsWith('.mp4')) {
      return 'video/mp4';
    } else if (urlLower.includes('.webm') || urlLower.endsWith('.webm')) {
      return 'video/webm';
    } else if (urlLower.includes('.ogg') || urlLower.endsWith('.ogv')) {
      return 'video/ogg';
    } else if (urlLower.includes('.mkv') || urlLower.endsWith('.mkv')) {
      return 'video/x-matroska';
    } else if (urlLower.includes('.m3u8')) {
      return 'application/x-mpegURL'; // HLS playlist
    }
    // Default: let browser try to detect
    return '';
  };

  const paginatedSegments = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedSegments.slice(start, start + rowsPerPage);
  }, [sortedSegments, page, rowsPerPage]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const columns: Column<Segment>[] = [
    { id: 'media', label: 'Media', sortable: false },
    { id: 'object_id', label: 'Object ID', sortable: true },
    { id: 'timerange', label: 'Timerange', sortable: true },
    { id: 'sample_offset', label: 'Sample Offset', sortable: true, align: 'right' },
    { id: 'sample_count', label: 'Sample Count', sortable: true, align: 'right' },
    { id: 'key_frame_count', label: 'Key Frames', sortable: true, align: 'right' },
    { id: 'links', label: 'Links', sortable: false },
  ];

  const renderRow = (segment: Segment, index: number) => {
    const firstUrl = getFirstPresignedUrl(segment);
    return (
      <>
        <TableCell sx={{ width: 200 }}>
          {firstUrl?.presigned && firstUrl?.url ? (
            <Box>
              {/* Hidden link for presigned URL */}
              <a 
                href={firstUrl.url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ display: 'none' }}
                aria-label="Presigned media URL"
              >
                {firstUrl.url}
              </a>
              
              {/* Video player widget */}
              <Box sx={{ maxWidth: 180, maxHeight: 120 }}>
                <video
                  controls
                  style={{
                    width: '100%',
                    maxHeight: '120px',
                    borderRadius: '4px',
                    backgroundColor: '#000'
                  }}
                  preload="metadata"
                  crossOrigin="anonymous"
                >
                  {(() => {
                    const mimeType = getVideoMimeType(firstUrl.url);
                    if (mimeType) {
                      return <source src={firstUrl.url} type={mimeType} />;
                    } else {
                      // Fallback: try multiple types or let browser detect
                      return (
                        <>
                          <source src={firstUrl.url} type="video/mp2t" />
                          <source src={firstUrl.url} type="video/mp4" />
                          <source src={firstUrl.url} type="video/webm" />
                          <source src={firstUrl.url} />
                        </>
                      );
                    }
                  })()}
                  Your browser does not support the video tag.
                </video>
              </Box>
            </Box>
          ) : (
            <Typography variant="caption" color="text.secondary">
              No media
            </Typography>
          )}
        </TableCell>
        <TableCell>
          <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
            {segment.object_id}
          </Typography>
        </TableCell>
        <TableCell>
          <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
            {segment.timerange?.value || '-'}
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="body2">
            {segment.sample_offset !== null && segment.sample_offset !== undefined 
              ? segment.sample_offset.toLocaleString() 
              : '-'}
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="body2">
            {segment.sample_count !== null && segment.sample_count !== undefined 
              ? segment.sample_count.toLocaleString() 
              : '-'}
          </Typography>
        </TableCell>
        <TableCell align="right">
          <Typography variant="body2">
            {segment.key_frame_count !== null && segment.key_frame_count !== undefined 
              ? segment.key_frame_count.toLocaleString() 
              : '-'}
          </Typography>
        </TableCell>
        <TableCell>
          {segment.get_urls && segment.get_urls.length > 0 ? (
            <Box>
              {segment.get_urls.map((urlInfo, urlIndex) => (
                <Box key={urlIndex} sx={{ mb: urlIndex < segment.get_urls!.length - 1 ? 1 : 0 }}>
                  {urlInfo.presigned ? (
                    <Typography 
                      variant="body2" 
                      component="a" 
                      href={urlInfo.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      sx={{ 
                        display: 'block',
                        color: 'primary.main',
                        textDecoration: 'none',
                        '&:hover': { textDecoration: 'underline' },
                        fontSize: '0.875rem'
                      }}
                    >
                      View Media
                    </Typography>
                  ) : (
                    <Typography 
                      variant="body2" 
                      component="a" 
                      href={urlInfo.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      sx={{ 
                        display: 'block',
                        color: 'primary.main',
                        textDecoration: 'none',
                        '&:hover': { textDecoration: 'underline' },
                        wordBreak: 'break-all',
                        fontSize: '0.875rem'
                      }}
                    >
                      {urlInfo.url}
                    </Typography>
                  )}
                  {urlInfo.label && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.75rem' }}>
                      {urlInfo.label}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">-</Typography>
          )}
        </TableCell>
      </>
    );
  };

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Segments
        </Typography>
      </Box>

      {filteredFlow && (
        <Card sx={{ mb: 2, backgroundColor: '#f5f5f5' }}>
          <CardContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Flow Information:
              </Typography>
              
              {/* Basic Info */}
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                  Basic Information:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip label={`ID: ${filteredFlow.id}`} size="small" variant="outlined" />
                  {filteredFlow.label && (
                    <Chip label={`Label: ${filteredFlow.label}`} size="small" variant="outlined" />
                  )}
                  <Chip label={`Format: ${filteredFlow.format}`} size="small" variant="outlined" color="primary" />
                  <Chip label={`Source ID: ${filteredFlow.source_id}`} size="small" variant="outlined" />
                  {filteredFlow.generation && (
                    <Chip label={`Generation: ${filteredFlow.generation}`} size="small" variant="outlined" />
                  )}
                </Box>
              </Box>

              {/* Codec & Container */}
              {(filteredFlow.codec || filteredFlow.container) && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Codec & Container:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {filteredFlow.codec && (
                      <Chip label={`Codec: ${filteredFlow.codec}`} size="small" variant="outlined" color="secondary" />
                    )}
                    {filteredFlow.container && (
                      <Chip label={`Container: ${filteredFlow.container}`} size="small" variant="outlined" color="secondary" />
                    )}
                  </Box>
                </Box>
              )}

              {/* Bit Rates */}
              {(filteredFlow.avg_bit_rate || filteredFlow.max_bit_rate) && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Bit Rates:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {filteredFlow.avg_bit_rate && (
                      <Chip 
                        label={`Avg: ${(filteredFlow.avg_bit_rate / 1000).toFixed(2)} Mbps`} 
                        size="small" 
                        variant="outlined" 
                        color="info"
                      />
                    )}
                    {filteredFlow.max_bit_rate && (
                      <Chip 
                        label={`Max: ${(filteredFlow.max_bit_rate / 1000).toFixed(2)} Mbps`} 
                        size="small" 
                        variant="outlined" 
                        color="info"
                      />
                    )}
                  </Box>
                </Box>
              )}

              {/* Duration */}
              {filteredFlow.segment_duration && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Segment Duration:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {filteredFlow.segment_duration.value || 
                     (filteredFlow.segment_duration.numerator && filteredFlow.segment_duration.denominator
                      ? `${filteredFlow.segment_duration.numerator}/${filteredFlow.segment_duration.denominator}`
                      : '-')}
                  </Typography>
                </Box>
              )}

              {/* Essence Parameters */}
              {filteredFlow.essence_parameters && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Essence Parameters:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {filteredFlow.essence_parameters.frame_width && filteredFlow.essence_parameters.frame_height && (
                      <Chip 
                        label={`Resolution: ${filteredFlow.essence_parameters.frame_width}x${filteredFlow.essence_parameters.frame_height}`} 
                        size="small" 
                        variant="outlined"
                      />
                    )}
                    {filteredFlow.essence_parameters.frame_rate && (
                      <Chip 
                        label={`Frame Rate: ${filteredFlow.essence_parameters.frame_rate.value || 
                          (filteredFlow.essence_parameters.frame_rate.numerator && filteredFlow.essence_parameters.frame_rate.denominator
                            ? `${filteredFlow.essence_parameters.frame_rate.numerator}/${filteredFlow.essence_parameters.frame_rate.denominator}`
                            : '-')}`} 
                        size="small" 
                        variant="outlined"
                      />
                    )}
                    {filteredFlow.essence_parameters.vfr && (
                      <Chip label="Variable Frame Rate" size="small" variant="outlined" color="warning" />
                    )}
                    {filteredFlow.essence_parameters.sample_rate && (
                      <Chip 
                        label={`Sample Rate: ${(filteredFlow.essence_parameters.sample_rate / 1000).toFixed(1)} kHz`} 
                        size="small" 
                        variant="outlined"
                      />
                    )}
                    {filteredFlow.essence_parameters.channels && (
                      <Chip 
                        label={`Channels: ${filteredFlow.essence_parameters.channels}`} 
                        size="small" 
                        variant="outlined"
                      />
                    )}
                    {filteredFlow.essence_parameters.bit_depth && (
                      <Chip 
                        label={`Bit Depth: ${filteredFlow.essence_parameters.bit_depth} bit`} 
                        size="small" 
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
              )}

              {/* Description */}
              {filteredFlow.description && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                    Description:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {filteredFlow.description}
                  </Typography>
                </Box>
              )}

              {/* Metadata */}
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {filteredFlow.created_by && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Created by:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {filteredFlow.created_by}
                    </Typography>
                  </Box>
                )}
                {filteredFlow.updated_by && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Updated by:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {filteredFlow.updated_by}
                    </Typography>
                  </Box>
                )}
                {filteredFlow.created && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Created:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(filteredFlow.created).toLocaleString()}
                    </Typography>
                  </Box>
                )}
                {filteredFlow.updated && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Updated:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(filteredFlow.updated).toLocaleString()}
                    </Typography>
                  </Box>
                )}
              </Box>

              {/* Tags */}
              {filteredFlow.tags && Object.keys(filteredFlow.tags).length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Tags:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {Object.entries(filteredFlow.tags).map(([key, value]) => (
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
          <Typography sx={{ ml: 2 }}>Loading segments...</Typography>
        </Box>
      ) : segments.length === 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 300, p: 4 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No segments found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', maxWidth: 500, mt: 1 }}>
            To view segments, please navigate to the <strong>Flows</strong> page and click <strong>"View Segments"</strong> on a flow to filter segments by that flow.
          </Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedSegments}
          getRowId={(segment) => segment.object_id}
          renderRow={renderRow}
          page={page}
          rowsPerPage={rowsPerPage}
          totalCount={sortedSegments.length}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          orderBy={orderBy}
          order={order}
          onSort={handleSort}
        />
      )}
    </Container>
  );
};

export default Segments;

