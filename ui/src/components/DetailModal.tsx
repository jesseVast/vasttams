import React, { useState } from 'react';
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
  IconButton,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import { Flow, Source } from '../types';
import TagEditModal from './TagEditModal';
import { sourceService, flowService } from '../services/api';

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  data: Flow | Source | null;
  title: string;
  onRefresh?: () => void; // Optional callback to refresh data after tag changes
  showTagEdit?: boolean; // Optional prop to show/hide tag edit button (default: true for flows, false for sources)
}

const DetailModal: React.FC<DetailModalProps> = ({ open, onClose, data, title, onRefresh, showTagEdit }) => {
  const [tagEditModalOpen, setTagEditModalOpen] = useState(false);
  const [localData, setLocalData] = useState<Flow | Source | null>(data);
  
  // Update local data when prop changes
  React.useEffect(() => {
    setLocalData(data);
  }, [data]);
  
  if (!localData) return null;

  const isFlow = 'source_id' in localData;

  const handleTagEdit = () => {
    setTagEditModalOpen(true);
  };

  const handleTagEditClose = () => {
    setTagEditModalOpen(false);
  };

  const handleTagSave = async () => {
    // Tags are saved immediately in TagEditModal
    // Reload the entity data to refresh tags display
    if (localData) {
      try {
        const service = isFlow ? flowService : sourceService;
        const refreshed = await service.get(localData.id);
        setLocalData(refreshed);
        
        // Also trigger parent refresh if callback provided
        if (onRefresh) {
          onRefresh();
        }
      } catch (error) {
        console.error('Failed to refresh data after tag update:', error);
      }
    }
    setTagEditModalOpen(false);
  };

  // Use localData instead of data throughout the component
  const displayData = localData;
  
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
          {displayData.label && (
            <Chip label={displayData.label} color="primary" size="small" />
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
                        {displayData.id}
                      </TableCell>
                    </TableRow>
                    {displayData.label && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Label</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{displayData.label}</TableCell>
                      </TableRow>
                    )}
                    {displayData.description && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Description</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{displayData.description}</TableCell>
                      </TableRow>
                    )}
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Format</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{displayData.format}</TableCell>
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
                            {(displayData as Flow).source_id}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Codec</TableCell>
                          <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                            {(displayData as Flow).codec || '-'}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Container</TableCell>
                          <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                            {(displayData as Flow).container || '-'}
                          </TableCell>
                        </TableRow>
                        {(displayData as Flow).avg_bit_rate !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Avg Bit Rate</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(displayData as Flow).avg_bit_rate?.toLocaleString() || '-'} {(displayData as Flow).avg_bit_rate ? 'bps' : ''}
                            </TableCell>
                          </TableRow>
                        )}
                        {(displayData as Flow).max_bit_rate !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Max Bit Rate</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(displayData as Flow).max_bit_rate?.toLocaleString() || '-'} {(displayData as Flow).max_bit_rate ? 'bps' : ''}
                            </TableCell>
                          </TableRow>
                        )}
                        {(displayData as Flow).generation !== undefined && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Generation</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(displayData as Flow).generation ?? '-'}
                            </TableCell>
                          </TableRow>
                        )}
                        {(displayData as Flow).metadata_version && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Metadata Version</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{(displayData as Flow).metadata_version}</TableCell>
                          </TableRow>
                        )}
                        {(displayData as Flow).segment_duration && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Segment Duration</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(() => {
                                const segDur = (displayData as Flow).segment_duration;
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
                        {(displayData as Flow).timerange && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Timerange</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                              {(() => {
                                const tr = (displayData as Flow).timerange;
                                if (typeof tr === 'string') return tr;
                                if (tr?.value) return tr.value;
                                if (tr?.start && tr?.end) return `${tr.start} to ${tr.end}`;
                                return JSON.stringify(tr, null, 2);
                              })()}
                            </TableCell>
                          </TableRow>
                        )}
                        {(displayData as Flow).flow_collection && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Flow Collection</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              {(() => {
                                const fc = (displayData as Flow).flow_collection;
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
                        {(displayData as Flow).collected_by && Array.isArray((displayData as Flow).collected_by) && (displayData as Flow).collected_by!.length > 0 && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Collected By</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              <Box>
                                {(displayData as Flow).collected_by!.map((flowId: string, idx: number) => (
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
                        {(displayData as Flow).container_mapping && (
                          <TableRow>
                            <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none', verticalAlign: 'top' }}>Container Mapping</TableCell>
                            <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                              <Box component="pre" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', margin: 0, whiteSpace: 'pre-wrap' }}>
                                {JSON.stringify((displayData as Flow).container_mapping, null, 2)}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>

                {/* Essence Parameters - Separate section for better visibility */}
                {(displayData as Flow).essence_parameters && (
                  <Paper sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                      Essence Parameters
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                    <Box sx={{ mt: 0.5 }}>
                      {formatEssenceParameters((displayData as Flow).essence_parameters)}
                    </Box>
                  </Paper>
                )}
              </>
            )}

            {/* Source-specific Information */}
            {!isFlow && (displayData as Source).source_collection && (
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Collections
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {(displayData as Source).source_collection?.map((item, idx) => (
                    <Chip key={idx} label={item.label || item.id} size="small" />
                  ))}
                </Box>
              </Paper>
            )}

            {/* Tags - Compact */}
            {(() => {
              // Handle tags that might be nested under 'root' or at top level
              const tags = displayData.tags;
              
              // Check if tags has a 'root' property with content
              const tagsToDisplay = tags?.root && typeof tags.root === 'object' 
                ? tags.root 
                : tags;
              
              // Check if there are any actual tag key-value pairs
              const hasTags = tagsToDisplay && typeof tagsToDisplay === 'object' 
                && Object.keys(tagsToDisplay).length > 0;
              
              // Determine if tag edit should be shown
              // Default: show for flows, hide for sources (unless explicitly set)
              const shouldShowTagEdit = showTagEdit !== undefined 
                ? showTagEdit 
                : isFlow;
              
              return (
                <Paper sx={{ p: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                      Tags
                    </Typography>
                    {shouldShowTagEdit && (
                      <IconButton
                        size="small"
                        onClick={handleTagEdit}
                        title="Edit tags"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    )}
                  </Box>
                  <Divider sx={{ mb: 1 }} />
                  {hasTags ? (
                    <Box sx={{ mt: 0.5 }}>
                      {formatObject(tagsToDisplay)}
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mt: 0.5 }}>
                      No tags defined
                    </Typography>
                  )}
                </Paper>
              );
            })()}

            {/* Metadata - Compact */}
            <Paper sx={{ p: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 0.5, fontSize: '0.9rem' }}>
                Metadata
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <TableContainer>
                <Table size="small">
                  <TableBody>
                    {displayData.created_by && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Created By</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{displayData.created_by}</TableCell>
                      </TableRow>
                    )}
                    {displayData.updated_by && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Updated By</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{displayData.updated_by}</TableCell>
                      </TableRow>
                    )}
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Created</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{formatDate(displayData.created)}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Updated</TableCell>
                      <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>{formatDate(displayData.updated)}</TableCell>
                    </TableRow>
                    {isFlow && (displayData as Flow).metadata_updated && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Metadata Updated</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                          {formatDate((displayData as Flow).metadata_updated)}
                        </TableCell>
                      </TableRow>
                    )}
                    {isFlow && (displayData as Flow).segments_updated && (
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold', width: '30%', py: 0.5, borderBottom: 'none' }}>Segments Updated</TableCell>
                        <TableCell sx={{ py: 0.5, borderBottom: 'none' }}>
                          {formatDate((displayData as Flow).segments_updated)}
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
      
      {/* Tag Edit Modal */}
      {displayData && (
        <TagEditModal
          open={tagEditModalOpen}
          onClose={handleTagEditClose}
          entityType={isFlow ? 'flow' : 'source'}
          entityId={displayData.id}
          entityLabel={displayData.label}
          onSave={handleTagSave}
        />
      )}
    </Dialog>
  );
};

export default DetailModal;

