import React, { useEffect, useState } from 'react';
import {
  Container,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Flow } from '../types';
import { flowService } from '../services/api';

const Flows: React.FC = () => {
  const [flows, setFlows] = useState<Flow[]>([]);

  useEffect(() => {
    loadFlows();
  }, []);

  const loadFlows = async () => {
    try {
      const data = await flowService.list();
      setFlows(data);
    } catch (error) {
      console.error('Failed to load flows:', error);
    }
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Flows
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Label</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Format</TableCell>
              <TableCell>Source ID</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {flows.map((flow) => (
              <TableRow key={flow.id}>
                <TableCell>{flow.id}</TableCell>
                <TableCell>{flow.label || '-'}</TableCell>
                <TableCell>{flow.description || '-'}</TableCell>
                <TableCell>{flow.format}</TableCell>
                <TableCell>{flow.source_id}</TableCell>
                <TableCell>{flow.created ? new Date(flow.created).toLocaleDateString() : '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
};

export default Flows;

