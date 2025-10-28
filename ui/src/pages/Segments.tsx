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
  TextField,
  Button,
} from '@mui/material';
import { Segment } from '../types';
import { segmentService } from '../services/api';

const Segments: React.FC = () => {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [flowId, setFlowId] = useState('');

  const loadSegments = async () => {
    if (!flowId) return;
    
    try {
      const data = await segmentService.listByFlow(flowId);
      setSegments(data);
    } catch (error) {
      console.error('Failed to load segments:', error);
    }
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Segments
      </Typography>

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
        <TextField
          label="Flow ID"
          value={flowId}
          onChange={(e) => setFlowId(e.target.value)}
          fullWidth
        />
        <Button 
          variant="contained" 
          onClick={loadSegments}
          sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
        >
          Load Segments
        </Button>
      </div>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Flow ID</TableCell>
              <TableCell>Object ID</TableCell>
              <TableCell>Timerange Start</TableCell>
              <TableCell>Timerange End</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {segments.map((segment) => (
              <TableRow key={segment.id}>
                <TableCell>{segment.id}</TableCell>
                <TableCell>{segment.flow_id}</TableCell>
                <TableCell>{segment.object_id}</TableCell>
                <TableCell>{segment.timerange?.start || '-'}</TableCell>
                <TableCell>{segment.timerange?.end || '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
};

export default Segments;

