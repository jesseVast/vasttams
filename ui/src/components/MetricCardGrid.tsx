import React from 'react';
import { Box } from '@mui/material';

interface MetricCardGridProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3 | 4 | 5 | 6;
  spacing?: number;
  sx?: any;
}

const MetricCardGrid: React.FC<MetricCardGridProps> = ({
  children,
  columns = 3,
  spacing = 2,
  sx = {},
}) => {

  const getGridSx = () => ({
    display: 'grid',
    gap: spacing,
    gridTemplateColumns: {
      xs: '1fr',
      sm: columns >= 2 ? 'repeat(2, 1fr)' : '1fr',
      md: columns >= 3 ? 'repeat(3, 1fr)' : `repeat(${Math.min(columns || 2, 2)}, 1fr)`,
      lg: columns === 5 
        ? 'repeat(5, 1fr)' 
        : `repeat(${columns || 3}, 1fr)`,
    },
    ...sx,
  });

  return (
    <Box sx={getGridSx()}>
      {children}
    </Box>
  );
};

export default MetricCardGrid;

