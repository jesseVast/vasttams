import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  TableSortLabel,
} from '@mui/material';

export type Order = 'asc' | 'desc';

export interface Column<T> {
  id: keyof T | string;
  label: string;
  sortable?: boolean;
  align?: 'left' | 'right' | 'center';
  render?: (value: any, row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  getRowId: (row: T) => string | number;
  renderRow: (row: T, index: number) => React.ReactNode;
  page: number;
  rowsPerPage: number;
  totalCount?: number; // Optional total count for pagination (if different from data.length)
  onPageChange: (event: unknown, newPage: number) => void;
  onRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  rowsPerPageOptions?: number[];
  orderBy?: keyof T | string;
  order?: Order;
  onSort?: (property: keyof T | string) => void;
}

function DataTable<T>({
  columns,
  data,
  getRowId,
  renderRow,
  page,
  rowsPerPage,
  totalCount,
  onPageChange,
  onRowsPerPageChange,
  rowsPerPageOptions = [5, 10, 25, 50, 100],
  orderBy,
  order,
  onSort,
}: DataTableProps<T>) {
  const handleSort = (property: keyof T | string) => {
    if (onSort) {
      onSort(property);
    }
  };

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell
                key={String(column.id)}
                align={column.align || 'left'}
              >
                {column.sortable && onSort ? (
                  <TableSortLabel
                    active={orderBy === column.id}
                    direction={orderBy === column.id ? order : 'asc'}
                    onClick={() => handleSort(column.id)}
                  >
                    {column.label}
                  </TableSortLabel>
                ) : (
                  column.label
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row, index) => (
            <TableRow
              key={getRowId(row)}
              sx={{ backgroundColor: index % 2 === 0 ? 'inherit' : 'action.hover' }}
            >
              {renderRow(row, index)}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <TablePagination
        component="div"
        count={totalCount !== undefined ? totalCount : data.length}
        page={page}
        onPageChange={onPageChange}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={onRowsPerPageChange}
        rowsPerPageOptions={rowsPerPageOptions}
      />
    </TableContainer>
  );
}

export default DataTable;

