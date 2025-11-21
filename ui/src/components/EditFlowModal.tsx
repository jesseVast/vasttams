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
} from '@mui/material';
import { Flow } from '../types';
import { flowService } from '../services/api';

interface EditFlowModalProps {
  open: boolean;
  onClose: () => void;
  flow: Flow | null;
  onSave: () => void;
}

const EditFlowModal: React.FC<EditFlowModalProps> = ({ open, onClose, flow, onSave }) => {
  const [formData, setFormData] = useState<Partial<Flow>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    }
  }, [flow]);

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
      <DialogTitle>Edit Flow</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
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
              rows={3}
              size="small"
            />

            <TextField
              label="Codec"
              value={formData.codec || ''}
              onChange={handleChange('codec')}
              fullWidth
              size="small"
              placeholder="e.g., h264, hevc, aac"
            />

            <TextField
              label="Container"
              value={formData.container || ''}
              onChange={handleChange('container')}
              fullWidth
              size="small"
              placeholder="e.g., mp4, mkv, ts"
            />

            <TextField
              label="Average Bit Rate (bps)"
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

            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                <strong>Note:</strong> Only editable fields are shown. Format, Source ID, and other system fields cannot be changed.
              </Typography>
            </Box>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditFlowModal;

