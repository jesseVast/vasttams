import React, { useEffect, useState, useMemo } from 'react';
import {
  Container,
  Typography,
  TableCell,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Box,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';
import { StorageBackend } from '../types';
import { storageBackendService } from '../services/api';
import DataTable, { Column, Order } from '../components/DataTable';

type SortableField = 'label' | 'provider' | 'store_type' | 'endpoint_url' | 'default_storage' | 'created_at';

const StorageBackends: React.FC = () => {
  const [backends, setBackends] = useState<StorageBackend[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingBackend, setEditingBackend] = useState<StorageBackend | null>(null);
  const [newBackend, setNewBackend] = useState<Partial<StorageBackend>>({
    label: '',
    store_type: 'http_object_store',
    provider: '',
    store_product: '',
    region: 'us-east-1',
    endpoint_url: '',
    bucket_name: '',
    root_path: '',
    use_ssl: false,
    default_storage: false,
  });
  const [editBackend, setEditBackend] = useState<Partial<StorageBackend>>({
    label: '',
    store_type: 'http_object_store',
    provider: '',
    store_product: '',
    region: 'us-east-1',
    endpoint_url: '',
    bucket_name: '',
    root_path: '',
    use_ssl: false,
    default_storage: false,
  });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState<SortableField>('label');
  const [order, setOrder] = useState<Order>('asc');

  useEffect(() => {
    loadBackends();
  }, []);

  const loadBackends = async () => {
    try {
      setLoading(true);
      const data = await storageBackendService.list();
      setBackends(data);
    } catch (error) {
      console.error('Failed to load storage backends:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setCreating(true);
      await storageBackendService.create(newBackend);
      setOpen(false);
      setNewBackend({
        label: '',
        store_type: 'http_object_store',
        provider: '',
        store_product: '',
        region: 'us-east-1',
        endpoint_url: '',
        bucket_name: '',
        root_path: '',
        use_ssl: false,
        default_storage: false,
      });
      loadBackends();
    } catch (error) {
      console.error('Failed to create storage backend:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this storage backend?')) {
      return;
    }
    try {
      setDeleting(id);
      await storageBackendService.delete(id);
      loadBackends();
    } catch (error: any) {
      console.error('Failed to delete storage backend:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete storage backend';
      alert(errorMessage);
    } finally {
      setDeleting(null);
    }
  };

  const handleEdit = (backend: StorageBackend) => {
    setEditingBackend(backend);
    setEditBackend({
      endpoint_url: backend.endpoint_url || '',
      bucket_name: backend.bucket_name || '',
      root_path: backend.root_path || '',
      use_ssl: backend.use_ssl || false,
      access_key: '', // Don't pre-fill for security
      secret_key: '', // Don't pre-fill for security
    });
    setEditOpen(true);
  };

  const handleUpdate = async () => {
    if (!editingBackend) return;

    try {
      setUpdating(true);
      // Only send fields that are set (exclude empty strings for keys)
      const updateData: any = {
        endpoint_url: editBackend.endpoint_url,
        bucket_name: editBackend.bucket_name,
        root_path: editBackend.root_path,
        use_ssl: editBackend.use_ssl,
      };
      if (editBackend.access_key) {
        updateData.access_key = editBackend.access_key;
      }
      if (editBackend.secret_key) {
        updateData.secret_key = editBackend.secret_key;
      }
      await storageBackendService.update(editingBackend.id, updateData);
      setEditOpen(false);
      setEditingBackend(null);
      setEditBackend({
        endpoint_url: '',
        use_ssl: false,
        access_key: '',
        secret_key: '',
      });
      loadBackends();
    } catch (error: any) {
      console.error('Failed to update storage backend:', error);
      alert(error.response?.data?.detail || error.message || 'Failed to update storage backend');
    } finally {
      setUpdating(false);
    }
  };

  const handleSort = (property: string | keyof StorageBackend) => {
    const sortField = property as SortableField;
    const isAsc = orderBy === sortField && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(sortField);
  };

  const sortedBackends = useMemo(() => {
    return [...backends].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'label':
          aValue = a.label || '';
          bValue = b.label || '';
          break;
        case 'provider':
          aValue = a.provider || '';
          bValue = b.provider || '';
          break;
        case 'store_type':
          aValue = a.store_type || '';
          bValue = b.store_type || '';
          break;
        case 'endpoint_url':
          aValue = a.endpoint_url || '';
          bValue = b.endpoint_url || '';
          break;
        case 'default_storage':
          aValue = a.default_storage ? 1 : 0;
          bValue = b.default_storage ? 1 : 0;
          break;
        case 'created_at':
          aValue = a.created_at ? new Date(a.created_at).getTime() : 0;
          bValue = b.created_at ? new Date(b.created_at).getTime() : 0;
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
  }, [backends, orderBy, order]);

  const paginatedBackends = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedBackends.slice(start, start + rowsPerPage);
  }, [sortedBackends, page, rowsPerPage]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const columns: Column<StorageBackend>[] = [
    { id: 'label', label: 'Label', sortable: true },
    { id: 'provider', label: 'Provider', sortable: true },
    { id: 'store_type', label: 'Store Type', sortable: true },
    { id: 'endpoint_url', label: 'Endpoint URL', sortable: true },
    { id: 'default_storage', label: 'Default', sortable: true },
    { id: 'created_at', label: 'Created', sortable: true },
    { id: 'actions', label: 'Actions', sortable: false },
  ];

  const renderRow = (backend: StorageBackend, index: number) => (
    <>
      <TableCell>{backend.label || '-'}</TableCell>
      <TableCell>{backend.provider}</TableCell>
      <TableCell>{backend.store_type}</TableCell>
      <TableCell>
        <Box sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {backend.endpoint_url || '-'}
        </Box>
      </TableCell>
      <TableCell>{backend.default_storage ? 'Yes' : 'No'}</TableCell>
      <TableCell>{backend.created_at ? new Date(backend.created_at).toLocaleDateString() : '-'}</TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            color="primary"
            startIcon={<EditIcon />}
            onClick={() => handleEdit(backend)}
          >
            Edit
          </Button>
          <Button
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => handleDelete(backend.id)}
            disabled={deleting === backend.id || backend.default_storage}
          >
            {deleting === backend.id ? <CircularProgress size={16} /> : 'Delete'}
          </Button>
        </Box>
      </TableCell>
    </>
  );

  return (
    <Container>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <Typography variant="h4">Storage Backends</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />} 
          onClick={() => setOpen(true)}
          sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
        >
          Add Storage Backend
        </Button>
      </div>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading storage backends...</Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedBackends}
          getRowId={(backend) => backend.id}
          renderRow={renderRow}
          page={page}
          rowsPerPage={rowsPerPage}
          totalCount={backends.length}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          orderBy={orderBy}
          order={order}
          onSort={handleSort}
        />
      )}

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Storage Backend</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Label"
            fullWidth
            variant="standard"
            value={newBackend.label}
            onChange={(e) => setNewBackend({ ...newBackend, label: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Store Type"
            fullWidth
            variant="standard"
            value={newBackend.store_type}
            onChange={(e) => setNewBackend({ ...newBackend, store_type: e.target.value })}
            required
          />
          <TextField
            margin="dense"
            label="Provider"
            fullWidth
            variant="standard"
            value={newBackend.provider}
            onChange={(e) => setNewBackend({ ...newBackend, provider: e.target.value })}
            required
          />
          <TextField
            margin="dense"
            label="Store Product"
            fullWidth
            variant="standard"
            value={newBackend.store_product}
            onChange={(e) => setNewBackend({ ...newBackend, store_product: e.target.value })}
            required
          />
          <TextField
            margin="dense"
            label="Region"
            fullWidth
            variant="standard"
            value={newBackend.region}
            onChange={(e) => setNewBackend({ ...newBackend, region: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Endpoint URL"
            fullWidth
            variant="standard"
            value={newBackend.endpoint_url}
            onChange={(e) => setNewBackend({ ...newBackend, endpoint_url: e.target.value })}
            placeholder="http://localhost:9000"
          />
          <TextField
            margin="dense"
            label="Bucket Name"
            fullWidth
            variant="standard"
            value={newBackend.bucket_name}
            onChange={(e) => setNewBackend({ ...newBackend, bucket_name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Root Path"
            fullWidth
            variant="standard"
            value={newBackend.root_path}
            onChange={(e) => setNewBackend({ ...newBackend, root_path: e.target.value })}
            placeholder="/tams8-dev"
          />
          <TextField
            margin="dense"
            label="Access Key"
            fullWidth
            variant="standard"
            type="password"
            value={newBackend.access_key || ''}
            onChange={(e) => setNewBackend({ ...newBackend, access_key: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Secret Key"
            fullWidth
            variant="standard"
            type="password"
            value={newBackend.secret_key || ''}
            onChange={(e) => setNewBackend({ ...newBackend, secret_key: e.target.value })}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={newBackend.use_ssl || false}
                onChange={(e) => setNewBackend({ ...newBackend, use_ssl: e.target.checked })}
              />
            }
            label="Use SSL"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={newBackend.default_storage || false}
                onChange={(e) => setNewBackend({ ...newBackend, default_storage: e.target.checked })}
              />
            }
            label="Default Storage"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCreate} 
            variant="contained" 
            disabled={creating || !newBackend.provider || !newBackend.store_product || !newBackend.store_type}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            {creating ? <CircularProgress size={20} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>
          <Typography variant="h6" component="div">
            Edit Storage Backend
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {editingBackend?.label || editingBackend?.id}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Connection and storage settings can be modified. Other fields are immutable to preserve object accessibility.
          </Typography>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Read-only info section */}
            <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, border: '1px solid', borderColor: 'grey.200' }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Immutable Fields
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mt: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Label</Typography>
                  <Typography variant="body2">{editingBackend?.label || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Provider</Typography>
                  <Typography variant="body2">{editingBackend?.provider || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Store Type</Typography>
                  <Typography variant="body2">{editingBackend?.store_type || '-'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Default Storage</Typography>
                  <Typography variant="body2">{editingBackend?.default_storage ? 'Yes' : 'No'}</Typography>
                </Box>
              </Box>
            </Box>

            {/* Editable fields */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>
              Connection & Storage Settings
            </Typography>
            <TextField
              label="Endpoint URL"
              fullWidth
              size="small"
              value={editBackend.endpoint_url || ''}
              onChange={(e) => setEditBackend({ ...editBackend, endpoint_url: e.target.value })}
              placeholder="http://localhost:9000"
            />
            <TextField
              label="Bucket Name"
              fullWidth
              size="small"
              value={editBackend.bucket_name || ''}
              onChange={(e) => setEditBackend({ ...editBackend, bucket_name: e.target.value })}
              placeholder="my-bucket"
            />
            <TextField
              label="Root Path"
              fullWidth
              size="small"
              value={editBackend.root_path || ''}
              onChange={(e) => setEditBackend({ ...editBackend, root_path: e.target.value })}
              placeholder="/tams8-dev"
              helperText="Path prefix for all objects in this backend"
            />
            <TextField
              label="Access Key"
              fullWidth
              size="small"
              type="password"
              value={editBackend.access_key || ''}
              onChange={(e) => setEditBackend({ ...editBackend, access_key: e.target.value })}
              helperText="Leave blank to keep current value"
            />
            <TextField
              label="Secret Key"
              fullWidth
              size="small"
              type="password"
              value={editBackend.secret_key || ''}
              onChange={(e) => setEditBackend({ ...editBackend, secret_key: e.target.value })}
              helperText="Leave blank to keep current value"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={editBackend.use_ssl || false}
                  onChange={(e) => setEditBackend({ ...editBackend, use_ssl: e.target.checked })}
                  size="small"
                />
              }
              label="Use SSL/TLS"
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => {
            setEditOpen(false);
            setEditingBackend(null);
            setEditBackend({
              endpoint_url: '',
              bucket_name: '',
              root_path: '',
              use_ssl: false,
              access_key: '',
              secret_key: '',
            });
          }}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpdate} 
            variant="contained" 
            disabled={updating}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            {updating ? <CircularProgress size={20} /> : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default StorageBackends;

