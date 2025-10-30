import React, { useState } from 'react';
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
  CircularProgress,
  Box,
} from '@mui/material';
import { Segment } from '../types';
import { segmentService } from '../services/api';

const Segments: React.FC = () => {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [flowId, setFlowId] = useState('');
  const [loading, setLoading] = useState(false);

  const loadSegments = async () => {
    if (!flowId) return;
    
    try {
      setLoading(true);
      const data = await segmentService.listByFlow(flowId);
      console.log('Loaded segments:', data);
      if (data && data.length > 0) {
        console.log('First segment:', data[0]);
        console.log('First segment get_urls:', data[0].get_urls);
      }
      setSegments(data);
    } catch (error) {
      console.error('Failed to load segments:', error);
    } finally {
      setLoading(false);
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
          disabled={loading}
          sx={{ backgroundColor: '#616161', '&:hover': { backgroundColor: '#757575' } }}
        >
          {loading ? <CircularProgress size={20} /> : 'Load Segments'}
        </Button>
      </div>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Loading segments...</Typography>
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Object ID</TableCell>
                <TableCell>Timerange</TableCell>
                <TableCell>Sample Offset</TableCell>
                <TableCell>Sample Count</TableCell>
                <TableCell>Key Frames</TableCell>
                <TableCell>URLs</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {segments.map((segment, index) => (
                <TableRow key={segment.object_id + '-' + index}>
                  <TableCell>{segment.object_id}</TableCell>
                  <TableCell>{segment.timerange?.value || '-'}</TableCell>
                  <TableCell>{segment.sample_offset ?? '-'}</TableCell>
                  <TableCell>{segment.sample_count ?? '-'}</TableCell>
                  <TableCell>{segment.key_frame_count ?? '-'}</TableCell>
                  <TableCell>
                    {segment.get_urls && segment.get_urls.length > 0 ? (
                      <Box>
                        {segment.get_urls.map((urlInfo, urlIndex) => (
                          <Box key={urlIndex} sx={{ mb: urlIndex < segment.get_urls!.length - 1 ? 1 : 0 }}>
                            <Typography 
                              variant="body2" 
                              component="a" 
                              href={urlInfo.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              sx={{ 
                                display: 'block',
                                color: 'primary.main',
                                textDecoration: 'none',
                                '&:hover': { textDecoration: 'underline' },
                                wordBreak: 'break-all'
                              }}
                            >
                              {urlInfo.url}
                            </Typography>
                            {urlInfo.label && (
                              <Typography variant="caption" color="text.secondary">
                                Label: {urlInfo.label}
                              </Typography>
                            )}
                            {urlInfo.presigned !== undefined && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                Presigned: {urlInfo.presigned ? 'Yes' : 'No'}
                              </Typography>
                            )}
                          </Box>
                        ))}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Container>
  );
};

export default Segments;

