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
        <Box sx={{ mt: 1 }}>
          <Stack spacing={2}>
            {/* Basic Information */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Basic Information
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                  <Typography variant="body2" color="text.secondary">
                    ID:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                    {data.id}
                  </Typography>
                </Box>
                {data.label && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Label:
                    </Typography>
                    <Typography variant="body2">{data.label}</Typography>
                  </Box>
                )}
                {data.description && (
                  <Box sx={{ flex: '1 1 100%' }}>
                    <Typography variant="body2" color="text.secondary">
                      Description:
                    </Typography>
                    <Typography variant="body2">{data.description}</Typography>
                  </Box>
                )}
                <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                  <Typography variant="body2" color="text.secondary">
                    Format:
                  </Typography>
                  <Typography variant="body2">{data.format}</Typography>
                </Box>
                {isFlow && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Source ID:
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {(data as Flow).source_id}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* Flow-specific Information */}
            {isFlow && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Flow Details
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  {(data as Flow).codec && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Codec:
                      </Typography>
                      <Typography variant="body2">{(data as Flow).codec}</Typography>
                    </Box>
                  )}
                  {(data as Flow).container && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Container:
                      </Typography>
                      <Typography variant="body2">{(data as Flow).container}</Typography>
                    </Box>
                  )}
                  {(data as Flow).avg_bit_rate && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Avg Bit Rate:
                      </Typography>
                      <Typography variant="body2">
                        {(data as Flow).avg_bit_rate?.toLocaleString()} bps
                      </Typography>
                    </Box>
                  )}
                  {(data as Flow).max_bit_rate && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Max Bit Rate:
                      </Typography>
                      <Typography variant="body2">
                        {(data as Flow).max_bit_rate?.toLocaleString()} bps
                      </Typography>
                    </Box>
                  )}
                  {(data as Flow).generation && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Generation:
                      </Typography>
                      <Typography variant="body2">{(data as Flow).generation}</Typography>
                    </Box>
                  )}
                  {(data as Flow).essence_parameters && (
                    <Box sx={{ flex: '1 1 100%' }}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        Essence Parameters:
                      </Typography>
                      <Box sx={{ mt: 0.5 }}>
                        {formatEssenceParameters((data as Flow).essence_parameters)}
                      </Box>
                    </Box>
                  )}
                  {(data as Flow).segment_duration && (
                    <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                      <Typography variant="body2" color="text.secondary">
                        Segment Duration:
                      </Typography>
                      <Typography variant="body2">
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
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Paper>
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

            {/* Tags */}
            {data.tags && Object.keys(data.tags).length > 0 && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Tags
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Box sx={{ mt: 1 }}>
                  {formatObject(data.tags)}
                </Box>
              </Paper>
            )}

            {/* Metadata */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Metadata
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {data.created_by && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Created By:
                    </Typography>
                    <Typography variant="body2">{data.created_by}</Typography>
                  </Box>
                )}
                {data.updated_by && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Updated By:
                    </Typography>
                    <Typography variant="body2">{data.updated_by}</Typography>
                  </Box>
                )}
                <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                  <Typography variant="body2" color="text.secondary">
                    Created:
                  </Typography>
                  <Typography variant="body2">{formatDate(data.created)}</Typography>
                </Box>
                <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                  <Typography variant="body2" color="text.secondary">
                    Updated:
                  </Typography>
                  <Typography variant="body2">{formatDate(data.updated)}</Typography>
                </Box>
                {isFlow && (data as Flow).metadata_updated && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Metadata Updated:
                    </Typography>
                    <Typography variant="body2">
                      {formatDate((data as Flow).metadata_updated)}
                    </Typography>
                  </Box>
                )}
                {isFlow && (data as Flow).segments_updated && (
                  <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)' } }}>
                    <Typography variant="body2" color="text.secondary">
                      Segments Updated:
                    </Typography>
                    <Typography variant="body2">
                      {formatDate((data as Flow).segments_updated)}
                    </Typography>
                  </Box>
                )}
              </Box>
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

