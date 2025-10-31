import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
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
  TableCell,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Link,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { Source } from '../types';
import { sourceService, authService } from '../services/api';
import DataTable, { Column } from '../components/DataTable';

type SortableField = 'id' | 'label' | 'format' | 'created';

const Sources: React.FC = () => {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const isViewer = user?.role === 'viewer';
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState<SortableField>('created');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
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
      setLoading(true);
      const data = await sourceService.list();
      setSources(data);
    } catch (error) {
      console.error('Failed to load sources:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : ((r & 0x3) | 0x8);
      return v.toString(16);
    });
  };

  const handleCreate = async () => {
    if (isViewer) {
      return; // Prevent viewers from creating sources
    }
    try {
      setCreating(true);
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
    } finally {
      setCreating(false);
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
        case 'id':
          aValue = a.id || '';
          bValue = b.id || '';
          break;
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
    { id: 'id', label: 'ID', sortable: true },
    { id: 'label', label: 'Label', sortable: true },
    { id: 'description', label: 'Description', sortable: false },
    { id: 'format', label: 'Format', sortable: true },
    { id: 'created', label: 'Created (Date/Time)', sortable: true },
    { id: 'actions', label: 'Actions', sortable: false },
  ];

  const renderRow = (source: Source, index: number) => (
    <>
      <TableCell>{source.id}</TableCell>
      <TableCell>{source.label || '-'}</TableCell>
      <TableCell>{source.description || '-'}</TableCell>
      <TableCell>{source.format}</TableCell>
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

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">
          Sources
        </Typography>
        {!isViewer && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpen(true)}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            Create Source
          </Button>
        )}
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

      <Dialog open={open && !isViewer} onClose={() => setOpen(false)}>
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
          <Button 
            onClick={handleCreate} 
            variant="contained" 
            disabled={creating || isViewer}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            {creating ? <CircularProgress size={20} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

    </Container>
  );
};

export default Sources;

