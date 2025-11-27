import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Chip,
  IconButton,
  Stack,
  Divider,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { Flow } from '../types';
import { flowService } from '../services/api';

interface EditFlowModalProps {
  open: boolean;
  onClose: () => void;
  flow: Flow | null;
  onSave: () => void;
}

interface TagEntry {
  name: string;
  value: string | string[];
  isArray: boolean;
}

const EditFlowModal: React.FC<EditFlowModalProps> = ({ open, onClose, flow, onSave }) => {
  const [formData, setFormData] = useState<Partial<Flow>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [tags, setTags] = useState<Record<string, TagEntry>>({});
  const [tagLoading, setTagLoading] = useState(false);
  const [tagSaving, setTagSaving] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);
  const [newTagName, setNewTagName] = useState('');
  const [newTagValue, setNewTagValue] = useState('');
  const [newTagIsArray, setNewTagIsArray] = useState(false);

  useEffect(() => {
    if (flow) {
      setFormData({
        codec: flow.codec || '',
        container: flow.container || '',
        label: flow.label || '',
        description: flow.description || '',
        avg_bit_rate: flow.avg_bit_rate,
        max_bit_rate: flow.max_bit_rate,
      });
      setError(null);
      setActiveTab(0); // Reset to first tab when flow changes
      loadTags();
    }
  }, [flow]);

  const loadTags = async () => {
    if (!flow) return;
    setTagLoading(true);
    setTagError(null);
    try {
      const tagsData = await flowService.getTags(flow.id);
      
      // Convert tags to TagEntry format
      const tagsMap: Record<string, TagEntry> = {};
      Object.entries(tagsData).forEach(([name, value]) => {
        const isArray = Array.isArray(value);
        tagsMap[name] = {
          name,
          value: isArray ? value : String(value),
          isArray,
        };
      });
      
      setTags(tagsMap);
    } catch (err: any) {
      console.error('Failed to load tags:', err);
      setTagError(err.response?.data?.detail || err.message || 'Failed to load tags');
    } finally {
      setTagLoading(false);
    }
  };

  const handleDeleteTag = async (tagName: string) => {
    if (!flow) return;
    setTagSaving(true);
    setTagError(null);
    try {
      await flowService.deleteTag(flow.id, tagName);
      
      // Remove from local state
      const newTags = { ...tags };
      delete newTags[tagName];
      setTags(newTags);
      
      // Trigger parent refresh
      onSave();
    } catch (err: any) {
      console.error('Failed to delete tag:', err);
      setTagError(err.response?.data?.detail || err.message || 'Failed to delete tag');
    } finally {
      setTagSaving(false);
    }
  };

  const handleAddTag = async () => {
    if (!flow || !newTagName.trim()) {
      setTagError('Tag name is required');
      return;
    }

    if (tags[newTagName]) {
      setTagError(`Tag "${newTagName}" already exists. Use update to modify it.`);
      return;
    }

    setTagSaving(true);
    setTagError(null);
    try {
      const value = newTagIsArray && newTagValue.trim()
        ? newTagValue.split(',').map(v => v.trim()).filter(v => v)
        : newTagValue.trim();

      if (newTagIsArray && (!Array.isArray(value) || value.length === 0)) {
        setTagError('Array tags must have at least one value (comma-separated)');
        setTagSaving(false);
        return;
      }

      await flowService.updateTag(flow.id, newTagName, value);

      // Add to local state
      setTags({
        ...tags,
        [newTagName]: {
          name: newTagName,
          value,
          isArray: newTagIsArray,
        },
      });

      // Reset form
      setNewTagName('');
      setNewTagValue('');
      setNewTagIsArray(false);

      // Trigger parent refresh
      onSave();
    } catch (err: any) {
      console.error('Failed to add tag:', err);
      setTagError(err.response?.data?.detail || err.message || 'Failed to add tag');
    } finally {
      setTagSaving(false);
    }
  };

  const formatTagValue = (value: string | string[]): string => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return String(value);
  };

  const handleChange = (field: keyof Flow) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.value;
    setFormData((prev) => ({
      ...prev,
      [field]: field === 'avg_bit_rate' || field === 'max_bit_rate' 
        ? (value === '' ? undefined : Number(value))
        : value,
    }));
  };

  const handleSave = async () => {
    if (!flow) return;

    setLoading(true);
    setError(null);

    try {
      // Prepare update data - only include fields that can be edited
      const updateData: Partial<Flow> = {
        id: flow.id,
        format: flow.format,
        source_id: flow.source_id,
        ...formData,
      };

      // Remove empty strings and convert to undefined
      Object.keys(updateData).forEach((key) => {
        const value = updateData[key as keyof Flow];
        if (value === '' || value === null) {
          delete updateData[key as keyof Flow];
        }
      });

      await flowService.update(flow.id, updateData);
      onSave();
      onClose();
    } catch (err: any) {
      console.error('Failed to update flow:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to update flow');
    } finally {
      setLoading(false);
    }
  };


  if (!flow) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>Edit Flow</DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 1.5 }}>
            {error}
          </Alert>
        )}

        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ mb: 1.5, minHeight: 40 }}>
          <Tab label="Properties" sx={{ minHeight: 40, textTransform: 'none' }} />
          <Tab label="Tags" sx={{ minHeight: 40, textTransform: 'none' }} />
        </Tabs>

        {activeTab === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <TextField
              label="Label"
              value={formData.label || ''}
              onChange={handleChange('label')}
              fullWidth
              size="small"
            />
            <TextField
              label="Description"
              value={formData.description || ''}
              onChange={handleChange('description')}
              fullWidth
              multiline
              rows={2}
              size="small"
            />
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <TextField
                label="Codec"
                value={formData.codec || ''}
                onChange={handleChange('codec')}
                fullWidth
                size="small"
                placeholder="e.g., h264, hevc"
              />
              <TextField
                label="Container"
                value={formData.container || ''}
                onChange={handleChange('container')}
                fullWidth
                size="small"
                placeholder="e.g., mp4, mkv, ts"
              />
            </Box>
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <TextField
                label="Avg Bit Rate (bps)"
                value={formData.avg_bit_rate || ''}
                onChange={handleChange('avg_bit_rate')}
                fullWidth
                size="small"
                type="number"
                inputProps={{ min: 0 }}
              />
              <TextField
                label="Max Bit Rate (bps)"
                value={formData.max_bit_rate || ''}
                onChange={handleChange('max_bit_rate')}
                fullWidth
                size="small"
                type="number"
                inputProps={{ min: 0 }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Only editable fields are shown. Format, Source ID, and other system fields cannot be changed.
            </Typography>
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            {tagError && (
              <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setTagError(null)}>
                {tagError}
              </Alert>
            )}

            {tagLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress size={24} />
              </Box>
            ) : (
              <>
                {/* Existing Tags */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, fontSize: '0.875rem' }}>
                    Existing Tags
                  </Typography>
                  {Object.keys(tags).length === 0 ? (
                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', fontSize: '0.8rem' }}>
                      No tags defined
                    </Typography>
                  ) : (
                    <Stack spacing={0.75}>
                      {Object.values(tags).map((tag) => (
                        <Box
                          key={tag.name}
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            p: 0.75,
                            border: '1px solid',
                            borderColor: 'divider',
                            borderRadius: 1,
                          }}
                        >
                          <Chip
                            label={tag.name}
                            color="primary"
                            variant="outlined"
                            size="small"
                            sx={{ fontSize: '0.75rem', height: 22 }}
                          />
                          <Typography variant="body2" sx={{ flex: 1, fontSize: '0.8rem' }}>
                            {tag.isArray ? '[' : ''}
                            {formatTagValue(tag.value)}
                            {tag.isArray ? ']' : ''}
                          </Typography>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteTag(tag.name)}
                            disabled={tagSaving}
                            sx={{ padding: '4px' }}
                            title="Delete tag"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Box>

                <Divider sx={{ my: 1.5 }} />

                {/* Add New Tag */}
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, fontSize: '0.875rem' }}>
                    Add New Tag
                  </Typography>
                  <Stack spacing={1.5}>
                    <TextField
                      label="Tag Name"
                      value={newTagName}
                      onChange={(e) => setNewTagName(e.target.value)}
                      fullWidth
                      size="small"
                      disabled={tagSaving}
                      placeholder="e.g., category, status"
                    />
                    <TextField
                      label="Tag Value"
                      value={newTagValue}
                      onChange={(e) => setNewTagValue(e.target.value)}
                      fullWidth
                      size="small"
                      disabled={tagSaving}
                      placeholder={newTagIsArray ? "Comma-separated values" : "Tag value"}
                      helperText={newTagIsArray ? "Enter comma-separated values for array tags" : "Enter a single value for string tags"}
                    />
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <input
                        type="checkbox"
                        id="isArray"
                        checked={newTagIsArray}
                        onChange={(e) => setNewTagIsArray(e.target.checked)}
                        disabled={tagSaving}
                      />
                      <label htmlFor="isArray">
                        <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>Array tag (comma-separated values)</Typography>
                      </label>
                    </Box>
                    <Button
                      variant="outlined"
                      startIcon={<AddIcon />}
                      onClick={handleAddTag}
                      disabled={tagSaving || !newTagName.trim()}
                      size="small"
                      sx={{ alignSelf: 'flex-start' }}
                    >
                      Add Tag
                    </Button>
                  </Stack>
                </Box>
              </>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 2, pb: 1.5, pt: 1 }}>
        <Button onClick={onClose} disabled={loading || tagSaving} size="small">
          Close
        </Button>
        {activeTab === 0 && (
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : null}
            size="small"
          >
            Save
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default EditFlowModal;




