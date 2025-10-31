import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  useTheme,
} from '@mui/material';

interface MetricCardProps {
  title: string;
  subtitle?: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  variant?: 'outlined' | 'elevation';
  size?: 'small' | 'medium' | 'large';
  children?: React.ReactNode;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  subtitle,
  value,
  unit,
  icon,
  color = 'primary',
  variant = 'elevation',
  size = 'medium',
  children,
}) => {
  const theme = useTheme();

  const getCardSx = () => {
    const baseSx = {
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      transition: 'all 0.2s ease-in-out',
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: theme.shadows[8],
      },
    };

    const sizeSx = {
      small: { minHeight: 80 },
      medium: { minHeight: 100 },
      large: { minHeight: 120 },
    };

    return { ...baseSx, ...sizeSx[size] };
  };

  const getValueSx = () => {
    const sizeSx = {
      small: { fontSize: '1.2rem', fontWeight: 600 },
      medium: { fontSize: '1.5rem', fontWeight: 700 },
      large: { fontSize: '1.8rem', fontWeight: 700 },
    };

    return {
      ...sizeSx[size],
      color: theme.palette[color].main,
      lineHeight: 1.2,
    };
  };

  return (
    <Card variant={variant} sx={getCardSx()}>
      <CardContent sx={{ 
        flexGrow: 1, 
        p: 1.5, 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, justifyContent: 'center' }}>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 24,
                height: 24,
                borderRadius: '50%',
                backgroundColor: 'grey.100',
                color: 'grey.600',
                mr: 1,
                flexShrink: 0,
                '& svg': {
                  fontSize: '1rem',
                },
              }}
            >
              {icon}
            </Box>
          )}
          <Box sx={{ textAlign: 'center', flexGrow: 1 }}>
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: 600,
                color: 'text.primary',
                mb: 0.5,
                fontSize: '0.875rem',
                lineHeight: 1.3,
              }}
            >
              {title}
            </Typography>
            {subtitle && (
              <Typography
                variant="caption"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  lineHeight: 1.3,
                  display: 'block',
                }}
              >
                {subtitle}
              </Typography>
            )}
          </Box>
        </Box>

        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          flexGrow: 1,
          textAlign: 'center',
          mb: 1
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'baseline', 
            justifyContent: 'center',
            flexWrap: 'wrap', 
            gap: 0.5 
          }}>
            <Typography sx={getValueSx()}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </Typography>
            {unit && (
              <Typography
                variant="body2"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  ml: 0.5,
                }}
              >
                {unit}
              </Typography>
            )}
          </Box>
        </Box>

        {children && (
          <Box sx={{ mt: 'auto', textAlign: 'center' }}>
            {children}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricCard;

