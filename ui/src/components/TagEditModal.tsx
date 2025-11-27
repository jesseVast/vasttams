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
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  Divider,
  Stack,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { sourceService, flowService } from '../services/api';

interface TagEditModalProps {
  open: boolean;
  onClose: () => void;
  entityType: 'source' | 'flow';
  entityId: string;
  entityLabel?: string;
  onSave: () => void;
}

interface TagEntry {
  name: string;
  value: string | string[];
  isArray: boolean;
}

const TagEditModal: React.FC<TagEditModalProps> = ({
  open,
  onClose,
  entityType,
  entityId,
  entityLabel,
  onSave,
}) => {
  const [tags, setTags] = useState<Record<string, TagEntry>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newTagName, setNewTagName] = useState('');
  const [newTagValue, setNewTagValue] = useState('');
  const [newTagIsArray, setNewTagIsArray] = useState(false);

  const service = entityType === 'source' ? sourceService : flowService;

  // Load tags when modal opens
  useEffect(() => {
    if (open && entityId) {
      loadTags();
    } else {
      // Reset state when modal closes
      setTags({});
      setNewTagName('');
      setNewTagValue('');
      setNewTagIsArray(false);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, entityId]);

  const loadTags = async () => {
    setLoading(true);
    setError(null);
    try {
      const tagsData = await service.getTags(entityId);
      
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
      setError(err.response?.data?.detail || err.message || 'Failed to load tags');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTag = async (tagName: string) => {
    setSaving(true);
    setError(null);
    try {
      await service.deleteTag(entityId, tagName);
      
      // Remove from local state
      const newTags = { ...tags };
      delete newTags[tagName];
      setTags(newTags);
      
      // Trigger parent refresh
      onSave();
    } catch (err: any) {
      console.error('Failed to delete tag:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to delete tag');
    } finally {
      setSaving(false);
    }
  };

  const handleAddTag = async () => {
    if (!newTagName.trim()) {
      setError('Tag name is required');
      return;
    }

    if (tags[newTagName]) {
      setError(`Tag "${newTagName}" already exists. Use update to modify it.`);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const value = newTagIsArray && newTagValue.trim()
        ? newTagValue.split(',').map(v => v.trim()).filter(v => v)
        : newTagValue.trim();

      if (newTagIsArray && (!Array.isArray(value) || value.length === 0)) {
        setError('Array tags must have at least one value (comma-separated)');
        setSaving(false);
        return;
      }

      await service.updateTag(entityId, newTagName, value);

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
      setError(err.response?.data?.detail || err.message || 'Failed to add tag');
    } finally {
      setSaving(false);
    }
  };

  const formatTagValue = (value: string | string[]): string => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return String(value);
  };

  const entityTitle = entityType === 'source' ? 'Source' : 'Flow';
  const displayName = entityLabel || entityId;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Edit Tags - {entityTitle}: {displayName}
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Existing Tags */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Existing Tags
              </Typography>
              {Object.keys(tags).length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                  No tags defined
                </Typography>
              ) : (
                <Stack spacing={1}>
                  {Object.values(tags).map((tag) => (
                    <Box
                      key={tag.name}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        p: 1,
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
                      />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {tag.isArray ? '[' : ''}
                        {formatTagValue(tag.value)}
                        {tag.isArray ? ']' : ''}
                      </Typography>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteTag(tag.name)}
                        disabled={saving}
                        title="Delete tag"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Add New Tag */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                Add New Tag
              </Typography>
              <Stack spacing={2}>
                <TextField
                  label="Tag Name"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  fullWidth
                  size="small"
                  disabled={saving}
                  placeholder="e.g., category, status, keywords"
                />
                <TextField
                  label="Tag Value"
                  value={newTagValue}
                  onChange={(e) => setNewTagValue(e.target.value)}
                  fullWidth
                  size="small"
                  disabled={saving}
                  placeholder={newTagIsArray ? "Comma-separated values (e.g., tag1, tag2, tag3)" : "Tag value"}
                  helperText={newTagIsArray ? "Enter comma-separated values for array tags" : "Enter a single value for string tags"}
                />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <input
                    type="checkbox"
                    id="isArray"
                    checked={newTagIsArray}
                    onChange={(e) => setNewTagIsArray(e.target.checked)}
                    disabled={saving}
                  />
                  <label htmlFor="isArray">
                    <Typography variant="body2">Array tag (comma-separated values)</Typography>
                  </label>
                </Box>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleAddTag}
                  disabled={saving || !newTagName.trim()}
                  size="small"
                >
                  Add Tag
                </Button>
              </Stack>
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TagEditModal;

