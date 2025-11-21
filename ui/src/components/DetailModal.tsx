import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
} from '@mui/material';
import { Flow, Source } from '../types';

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  data: Flow | Source | null;
  title: string;
}

const DetailModal: React.FC<DetailModalProps> = ({ open, onClose, data, title }) => {
  if (!data) return null;

  const isFlow = 'source_id' in data;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return String(value);
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(', ') : '-';
    }
    if (typeof value === 'object') {
      // Handle SegmentDuration objects (frame_rate, aspect_ratio, pixel_aspect_ratio)
      if (value.value !== undefined) {
        return value.value;
      }
      if (value.numerator !== undefined && value.denominator !== undefined) {
        return `${value.numerator}/${value.denominator}`;
      }
      if (value.numerator !== undefined) {
        return String(value.numerator);
      }
      // For nested objects, show as formatted JSON
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const formatEssenceParameters = (params: any): React.ReactNode => {
    if (!params || typeof params !== 'object') return null;

    const rows: Array<{ key: string; value: string | React.ReactNode }> = [];

    // Process all fields in the essence_parameters object
    Object.entries(params).forEach(([key, value]) => {
      if (value === null || value === undefined) return;

      // Format key name (capitalize first letter, replace underscores with spaces)
      const formattedKey = key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

      let displayValue: string | React.ReactNode = formatValue(value);

      // Special formatting for specific fields
      if (key === 'frame_width' || key === 'frame_height') {
        displayValue = `${displayValue} px`;
      } else if (key === 'sample_rate') {
        displayValue = `${Number(value).toLocaleString()} Hz`;
      } else if (key === 'bit_depth') {
        displayValue = `${displayValue} bits`;
      } else if (key === 'frame_rate' || key === 'aspect_ratio' || key === 'pixel_aspect_ratio') {
        // These are handled by formatValue for SegmentDuration objects
        displayValue = formatValue(value);
      } else if (key === 'vfr') {
        displayValue = value ? 'Yes' : 'No';
      } else if (typeof value === 'object' && !Array.isArray(value) && value.constructor === Object) {
        // Nested objects like codec_parameters, unc_parameters
        // Display as a formatted table or JSON
        if (Object.keys(value).length > 0) {
          displayValue = (
            <Box component="pre" sx={{ 
              fontFamily: 'monospace', 
              fontSize: '0.75rem', 
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {JSON.stringify(value, null, 2)}
            </Box>
          );
        } else {
          displayValue = '-';
        }
      }

      rows.push({ 
        key: formattedKey,
        value: displayValue
      });
    });

    if (rows.length === 0) return null;

    return (
      <TableContainer>
        <Table size="small">
          <TableBody>
            {rows.map((row, idx) => (
              <TableRow key={idx}>
                <TableCell sx={{ fontWeight: 'bold', width: '40%', borderBottom: idx === rows.length - 1 ? 'none' : undefined, verticalAlign: 'top' }}>
                  {row.key}
                </TableCell>
                <TableCell sx={{ borderBottom: idx === rows.length - 1 ? 'none' : undefined, verticalAlign: 'top' }}>
                  {row.value}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  const formatObject = (obj: any, depth = 0): React.ReactNode => {
    if (obj === null || obj === undefined) return '-';
    if (typeof obj === 'string') return obj;
    if (typeof obj === 'number' || typeof obj === 'boolean') return String(obj);
    if (Array.isArray(obj)) {
      if (obj.length === 0) return '-';
      return (
        <Box>
          {obj.map((item, idx) => (
            <Box key={idx} sx={{ mb: 0.5 }}>
              {formatObject(item, depth + 1)}
            </Box>
          ))}
        </Box>
      );
    }
    if (typeof obj === 'object') {
      return (
        <Box sx={{ pl: depth > 0 ? 2 : 0 }}>
          {Object.entries(obj).map(([key, value]) => (
            <Box key={key} sx={{ mb: 0.5 }}>
              <Typography variant="body2" component="span" sx={{ fontWeight: 'bold' }}>
                {key}:
              </Typography>{' '}
              <Typography variant="body2" component="span">
                {formatObject(value, depth + 1)}
              </Typography>
            </Box>
          ))}
        </Box>
      );
    }
    return String(obj);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">{title}</Typography>
          {data.label && (
            <Chip label={data.label} color="primary" size="small" />
          )}
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 0.5 }}>
          <Stack spacing={1.5}>
            {/* Basic Information - Compact */}
            <Paper sx={{ p: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                Basic Information
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>ID</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', py: 0.5, borderBottom: 'none' }}>
                        {data.id}
                      </TableCell>
                    </TableRow>
                    {data.label && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Label</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{data.label}</TableCell>
                      </TableRow>
                    )}
                    {data.description && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Description</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{data.description}</TableCell>
                      </TableRow>
                    )}
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Format</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{data.format}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>

            {/* Flow-specific Information - Comprehensive */}
            {isFlow && (
              <>
                <Paper sx={{ p: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                    Flow Details
                  </Typography>
                  <Divider sx={{ mb: 1 }} />
                  <TableContainer>
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Source ID</TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', py: 0.5, borderBottom: 'none' }}>
                            {(data as Flow).source_id}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Codec</TableCell>
                          <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                            {(data as Flow).codec || '-'}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Container</TableCell>
                          <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                            {(data as Flow).container || '-'}
                          </TableCell>
                        </TableRow>
                        {(data as Flow).avg_bit_rate !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Avg Bit Rate</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(data as Flow).avg_bit_rate?.toLocaleString() || '-'} {(data as Flow).avg_bit_rate ? 'bps' : ''}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).max_bit_rate !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Max Bit Rate</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(data as Flow).max_bit_rate?.toLocaleString() || '-'} {(data as Flow).max_bit_rate ? 'bps' : ''}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).generation !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Generation</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(data as Flow).generation ?? '-'}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).metadata_version && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Metadata Version</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{(data as Flow).metadata_version}</TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).segment_duration && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Segment Duration</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(() => {
                                const segDur = (data as Flow).segment_duration;
                                if (segDur?.value) {
                                  return segDur.value;
                                }
                                if (segDur?.numerator !== undefined && segDur?.denominator !== undefined) {
                                  return `${segDur.numerator}/${segDur.denominator}`;
                                }
                                return '-';
                              })()}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).timerange && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Timerange</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                              {(() => {
                                const tr = (data as Flow).timerange;
                                if (typeof tr === 'string') return tr;
                                if (tr?.value) return tr.value;
                                if (tr?.start && tr?.end) return `${tr.start} to ${tr.end}`;
                                return JSON.stringify(tr, null, 2);
                              })()}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).flow_collection && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Flow Collection</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(() => {
                                const fc = (data as Flow).flow_collection;
                                if (Array.isArray(fc)) {
                                  return (
                                    <Box>
                                      {fc.map((item: any, idx: number) => (
                                        <Chip
                                          key={idx}
                                          label={item.label || item.id || JSON.stringify(item)}
                                          size="small"
                                          sx={{ mr: 0.5, mb: 0.5 }}
                                        />
                                      ))}
                                    </Box>
                                  );
                                }
                                if (typeof fc === 'object') {
                                  return (
                                    <Box component="pre" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', margin: 0, whiteSpace: 'pre-wrap' }}>
                                      {JSON.stringify(fc, null, 2)}
                                    </Box>
                                  );
                                }
                                return String(fc);
                              })()}
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).collected_by && Array.isArray((data as Flow).collected_by) && (data as Flow).collected_by!.length > 0 && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Collected By</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              <Box>
                                {(data as Flow).collected_by!.map((flowId: string, idx: number) => (
                                  <Chip
                                    key={idx}
                                    label={flowId}
                                    size="small"
                                    sx={{ mr: 0.5, mb: 0.5, fontFamily: 'monospace', fontSize: '0.7rem' }}
                                  />
                                ))}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                        {(data as Flow).container_mapping && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Container Mapping</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              <Box component="pre" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', margin: 0, whiteSpace: 'pre-wrap' }}>
                                {JSON.stringify((data as Flow).container_mapping, null, 2)}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>

                {/* Essence Parameters - Separate section for better visibility */}
                {(data as Flow).essence_parameters && (
                  <Paper sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                      Essence Parameters
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                    <Box sx={{ mt: 0.5 }}>
                      {formatEssenceParameters((data as Flow).essence_parameters)}
                    </Box>
                  </Paper>
                )}
              </>
            )}

            {/* Source-specific Information */}
            {!isFlow && (data as Source).source_collection && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Collections
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {(data as Source).source_collection?.map((item, idx) => (
                    <Chip key={idx} label={item.label || item.id} size="small" />
                  ))}
                </Box>
              </Paper>
            )}

            {/* Tags - Compact */}
            {data.tags && Object.keys(data.tags).length > 0 && (
              <Paper sx={{ p: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                  Tags
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Box sx={{ mt: 0.5 }}>
                  {formatObject(data.tags)}
                </Box>
              </Paper>
            )}

            {/* Metadata - Compact */}
            <Paper sx={{ p: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                Metadata
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    {data.created_by && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Created By</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{data.created_by}</TableCell>
                      </TableRow>
                    )}
                    {data.updated_by && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Updated By</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{data.updated_by}</TableCell>
                      </TableRow>
                    )}
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Created</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{formatDate(data.created)}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Updated</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{formatDate(data.updated)}</TableCell>
                    </TableRow>
                    {isFlow && (data as Flow).metadata_updated && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Metadata Updated</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                          {formatDate((data as Flow).metadata_updated)}
                        </TableCell>
                      </TableRow>
                    )}
                    {isFlow && (data as Flow).segments_updated && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Segments Updated</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                          {formatDate((data as Flow).segments_updated)}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default DetailModal;

