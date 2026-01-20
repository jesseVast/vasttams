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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Box,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';
import { User } from '../types';
import { userService } from '../services/api';
import DataTable, { Column, Order } from '../components/DataTable';

type SortableField = 'username' | 'role' | 'created_at';

const DEFAULT_USERS = ['admin', 'editor', 'viewer'];

const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newUser, setNewUser] = useState({ username: '', role: 'viewer' as const, password: '' });
  const [editUser, setEditUser] = useState({ role: 'viewer' as const, password: '' });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState<SortableField>('username');
  const [order, setOrder] = useState<Order>('asc');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await userService.list();
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setCreating(true);
      await userService.create(newUser.username, newUser.role, newUser.password);
      setOpen(false);
      setNewUser({ username: '', role: 'viewer', password: '' });
      loadUsers();
    } catch (error) {
      console.error('Failed to create user:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (username: string) => {
    try {
      setDeleting(username);
      await userService.delete(username);
      
      // Update local state immediately instead of reloading
      setUsers(prevUsers => prevUsers.filter(user => user.username !== username));
      
      // Adjust page if needed (if we deleted the last item on the current page)
      setPage(prevPage => {
        const remainingCount = users.length - 1;
        const maxPage = Math.max(0, Math.ceil(remainingCount / rowsPerPage) - 1);
        return Math.min(prevPage, maxPage);
      });
    } catch (error) {
      console.error('Failed to delete user:', error);
    } finally {
      setDeleting(null);
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setEditUser({ role: user.role as any, password: '' });
    setEditOpen(true);
  };

  const handleUpdate = async () => {
    if (!editingUser) return;

    try {
      setUpdating(true);
      
      // Update role if changed
      if (editUser.role !== editingUser.role) {
        await userService.updateRole(editingUser.username, editUser.role);
      }
      
      // Update password if provided
      if (editUser.password && editUser.password.trim() !== '') {
        await userService.updatePassword(editingUser.username, editUser.password);
      }
      
      setEditOpen(false);
      setEditingUser(null);
      setEditUser({ role: 'viewer', password: '' });
      loadUsers();
    } catch (error) {
      console.error('Failed to update user:', error);
    } finally {
      setUpdating(false);
    }
  };

  const handleSort = (property: string | keyof User) => {
    const sortField = property as SortableField;
    const isAsc = orderBy === sortField && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(sortField);
  };

  const sortedUsers = useMemo(() => {
    return [...users].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'username':
          aValue = a.username || '';
          bValue = b.username || '';
          break;
        case 'role':
          aValue = a.role || '';
          bValue = b.role || '';
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
  }, [users, orderBy, order]);

  const paginatedUsers = useMemo(() => {
    const start = page * rowsPerPage;
    return sortedUsers.slice(start, start + rowsPerPage);
  }, [sortedUsers, page, rowsPerPage]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const columns: Column<User>[] = [
    { id: 'username', label: 'Username', sortable: true },
    { id: 'role', label: 'Role', sortable: true },
    { id: 'created_at', label: 'Created', sortable: true },
    { id: 'actions', label: 'Actions', sortable: false },
  ];

  const renderRow = (user: User, index: number) => (
    <>
      <TableCell>{user.username}</TableCell>
      <TableCell>{user.role}</TableCell>
      <TableCell>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            color="primary"
            startIcon={<EditIcon />}
            onClick={() => handleEdit(user)}
          >
            Edit
          </Button>
          <Button
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => handleDelete(user.username)}
            disabled={deleting === user.username || DEFAULT_USERS.includes(user.username)}
          >
            {deleting === user.username ? <CircularProgress size={16} /> : 'Delete'}
          </Button>
        </Box>
      </TableCell>
    </>
  );

  return (
    <Container>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <Typography variant="h4">Users</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />} 
          onClick={() => setOpen(true)}
          sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
        >
          Add User
        </Button>
      </div>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading users...</Typography>
        </Box>
      ) : (
        <DataTable
          columns={columns}
          data={paginatedUsers}
          getRowId={(user) => user.user_id}
          renderRow={renderRow}
          page={page}
          rowsPerPage={rowsPerPage}
          totalCount={users.length}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          orderBy={orderBy}
          order={order}
          onSort={handleSort}
        />
      )}

      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Add User</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Username"
            fullWidth
            variant="standard"
            value={newUser.username}
            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Role</InputLabel>
            <Select
              value={newUser.role}
              label="Role"
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value as any })}
            >
              <MenuItem value="viewer">Viewer</MenuItem>
              <MenuItem value="editor">Editor</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="Password"
            type="password"
            fullWidth
            variant="standard"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCreate} 
            variant="contained" 
            disabled={creating}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            {creating ? <CircularProgress size={20} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)}>
        <DialogTitle>Edit User: {editingUser?.username}</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal">
            <InputLabel>Role</InputLabel>
            <Select
              value={editUser.role}
              label="Role"
              onChange={(e) => setEditUser({ ...editUser, role: e.target.value as any })}
            >
              <MenuItem value="viewer">Viewer</MenuItem>
              <MenuItem value="editor">Editor</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="New Password (leave blank to keep current)"
            type="password"
            fullWidth
            variant="standard"
            value={editUser.password}
            onChange={(e) => setEditUser({ ...editUser, password: e.target.value })}
            helperText="Leave blank if you don't want to change the password"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setEditOpen(false);
            setEditingUser(null);
            setEditUser({ role: 'viewer', password: '' });
          }}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpdate} 
            variant="contained" 
            disabled={updating}
            sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
          >
            {updating ? <CircularProgress size={20} /> : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Users;

