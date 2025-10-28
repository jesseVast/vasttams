import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import InfoIcon from '@mui/icons-material/Info';
import { Source } from '../types';
import { sourceService } from '../services/api';

const Sources: React.FC = () => {
  const [sources, setSources] = useState<Source[]>([]);
  const [open, setOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [formData, setFormData] = useState({
    label: '',
    description: '',
    format: 'urn:x-nmos:format:video',
    created_by: '',
  });

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const data = await sourceService.list();
      setSources(data);
    } catch (error) {
      console.error('Failed to load sources:', error);
    }
  };

  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const handleCreate = async () => {
    try {
      const id = generateUUID();
      const now = new Date().toISOString();
      const sourceData = {
        id,
        ...formData,
        created: now,
        updated: now,
        created_by: formData.created_by || 'admin',
        updated_by: formData.created_by || 'admin',
      };
      await sourceService.create(sourceData);
      setOpen(false);
      setFormData({ label: '', description: '', format: 'urn:x-nmos:format:video', created_by: '' });
      loadSources();
    } catch (error) {
      console.error('Failed to create source:', error);
    }
  };

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Sources
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpen(true)}
          sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
        >
          Create Source
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Label</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Format</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sources.map((source) => (
              <TableRow key={source.id}>
                <TableCell>{source.id}</TableCell>
                <TableCell>{source.label || '-'}</TableCell>
                <TableCell>{source.description || '-'}</TableCell>
                <TableCell>{source.format}</TableCell>
                <TableCell>{source.created ? new Date(source.created).toLocaleDateString() : '-'}</TableCell>
                <TableCell>
                  <Button
                    size="small"
                    startIcon={<InfoIcon />}
                    onClick={() => {
                      setSelectedSource(source);
                      setDetailsOpen(true);
                    }}
                  >
                    Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Create Source</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Label"
            fullWidth
            variant="standard"
            value={formData.label}
            onChange={(e) => setFormData({ ...formData, label: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            variant="standard"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
          <FormControl fullWidth variant="standard" margin="dense">
            <InputLabel>Format</InputLabel>
            <Select
              value={formData.format}
              onChange={(e) => setFormData({ ...formData, format: e.target.value })}
            >
              <MenuItem value="urn:x-nmos:format:video">Video</MenuItem>
              <MenuItem value="urn:x-nmos:format:audio">Audio</MenuItem>
              <MenuItem value="urn:x-nmos:format:data">Data</MenuItem>
              <MenuItem value="urn:x-nmos:format:multi">Multi</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="Created By"
            fullWidth
            variant="standard"
            value={formData.created_by}
            onChange={(e) => setFormData({ ...formData, created_by: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}>
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Source Details</DialogTitle>
        <DialogContent>
          {selectedSource && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>ID:</strong> {selectedSource.id}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Label:</strong> {selectedSource.label || '-'}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Description:</strong> {selectedSource.description || '-'}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Format:</strong> {selectedSource.format}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Created By:</strong> {selectedSource.created_by || '-'}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Updated By:</strong> {selectedSource.updated_by || '-'}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Created:</strong> {selectedSource.created ? new Date(selectedSource.created).toLocaleString() : '-'}</DialogContentText>
              </Box>
              <Box sx={{ mb: 2 }}>
                <DialogContentText><strong>Updated:</strong> {selectedSource.updated ? new Date(selectedSource.updated).toLocaleString() : '-'}</DialogContentText>
              </Box>
              {selectedSource.tags && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}><strong>Tags:</strong></Typography>
                  <Paper sx={{ p: 2, maxHeight: 200, overflow: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                      {JSON.stringify(selectedSource.tags, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Sources;

