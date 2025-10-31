import React from 'react';
import { Paper, Typography } from '@mui/material';

interface StatCardProps {
  value: string | number;
  label: string;
}

const StatCard: React.FC<StatCardProps> = ({ value, label }) => {
  return (
    <Paper sx={{ 
      p: 3, 
      textAlign: 'center', 
      width: '200px',
      minWidth: '200px',
      maxWidth: '200px'
    }}>
      <Typography variant="h4" color="primary">
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Paper>
  );
};

export default StatCard;

