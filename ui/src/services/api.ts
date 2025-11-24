import axios from 'axios';
import { User, Source, Flow, Segment, AuthResponse, AnalyticsSummary } from '../types';

// Single API base URL that includes the full path to the API
// Docker: REACT_APP_API_URL=/api -> API_BASE_URL=/api/tams/v8.0
// Local: REACT_APP_API_URL=http://docker1:8000 -> API_BASE_URL=http://docker1:8000/api/tams/v8.0
const REACT_APP_API_URL = process.env.REACT_APP_API_URL || 'http://docker1:8000';
const API_VERSION_PATH = '/tams/v8.0';

// Construct full API base URL
export const API_BASE_URL = REACT_APP_API_URL === '/api'
  ? `${REACT_APP_API_URL}${API_VERSION_PATH}`  // Docker: /api/tams/v8.0
  : `${REACT_APP_API_URL}/api${API_VERSION_PATH}`;  // Local: http://docker1:8000/api/tams/v8.0

// Log the API URL being used (only in development)
if (process.env.NODE_ENV === 'development') {
  console.log('[API Config] API_BASE_URL:', API_BASE_URL);
  console.log('[API Config] REACT_APP_API_URL env var:', REACT_APP_API_URL);
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined' && window.localStorage) {
    const token = localStorage.getItem('token');
    if (token) {
      (config.headers as any).Authorization = `Bearer ${token}`;
    }
  }
  
  // Performance instrumentation for API calls
  if (config.url?.includes('/segments')) {
    const requestId = `api-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    (config as any).__requestId = requestId;
    (config as any).__startTime = performance.now();
    performance.mark(`${requestId}-request-start`);
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url} - Request started`);
  }
  
  return config;
});

// Logout and redirect on auth failures
api.interceptors.response.use(
  (response) => {
    // Performance instrumentation for API responses
    const config = response.config as any;
    if (config?.__requestId && config.url?.includes('/segments')) {
      const duration = performance.now() - config.__startTime;
      performance.mark(`${config.__requestId}-response-end`);
      performance.measure(`${config.__requestId}-duration`, `${config.__requestId}-request-start`, `${config.__requestId}-response-end`);
      const dataLength = JSON.stringify(response.data).length;
      const itemCount = Array.isArray(response.data?.data) ? response.data.data.length : (Array.isArray(response.data) ? response.data.length : 'N/A');
      const dataSizeKB = (dataLength / 1024).toFixed(2);
      const rate = typeof itemCount === 'number' && duration > 0 ? (itemCount / (duration / 1000)).toFixed(2) : 'N/A';
      
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url} - Response received: ${duration.toFixed(2)}ms, ${dataSizeKB} KB, ${itemCount} items${typeof rate === 'string' && rate !== 'N/A' ? `, ${rate} items/sec` : ''}`);
      
      // Log detailed timing if available
      if (response.headers && typeof performance !== 'undefined') {
        const timing = (performance as any).getEntriesByName?.(config.__requestId + '-request-start', 'mark');
        if (timing && timing.length > 0) {
          const networkTiming = performance.getEntriesByType('resource').find((entry: any) => 
            entry.name.includes(config.url || '')
          ) as PerformanceResourceTiming | undefined;
          
          if (networkTiming) {
            console.log(`[API] Network breakdown:`, {
              dns: `${(networkTiming.domainLookupEnd - networkTiming.domainLookupStart).toFixed(2)}ms`,
              connect: `${(networkTiming.connectEnd - networkTiming.connectStart).toFixed(2)}ms`,
              request: `${(networkTiming.responseStart - networkTiming.requestStart).toFixed(2)}ms`,
              response: `${(networkTiming.responseEnd - networkTiming.responseStart).toFixed(2)}ms`,
              total: `${(networkTiming.responseEnd - networkTiming.requestStart).toFixed(2)}ms`,
            });
          }
        }
      }
    }
    return response;
  },
  (error) => {
    // Performance instrumentation for API errors
    const config = error?.config as any;
    if (config?.__requestId && config.url?.includes('/segments')) {
      const duration = performance.now() - config.__startTime;
      console.error(`[API] ${config.method?.toUpperCase()} ${config.url} - Error after ${duration.toFixed(2)}ms:`, error.message);
    }
    
    const status = error?.response?.status;
    const path = window.location.pathname;
    const isAuthRoute = path.toLowerCase().includes('/login');

    // Treat 401/403 as invalid/expired token
    if ((status === 401 || status === 403) && !isAuthRoute) {
      try {
        // Clear stored auth
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      } catch {}
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.replace('/login');
      }
    }

    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    try {
      const response = await api.post('/auth/login', {
        username,
        password,
      });
      return response.data;
    } catch (error: any) {
      console.error('Login error:', error);
      throw error;
    }
  },

  logout: () => {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  },

  getCurrentUser: (): User | null => {
    if (typeof window !== 'undefined' && window.localStorage) {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    }
    return null;
  },
};

export const userService = {
  list: async (): Promise<User[]> => {
    const response = await api.get('/users');
    return response.data || [];
  },

  create: async (username: string, role: string, password: string): Promise<User> => {
    const response = await api.post('/users', {
      username,
      password,
      role,
    });
    return response.data;
  },

  delete: async (username: string): Promise<void> => {
    await api.delete(`/users/${username}`);
  },

  updateRole: async (username: string, role: string): Promise<void> => {
    await api.put(`/users/${username}/role`, { role });
  },

  updatePassword: async (username: string, password: string): Promise<void> => {
    await api.put(`/users/${username}/password`, { password });
  },
};

export const sourceService = {
  list: async (): Promise<Source[]> => {
    // source_collection is computed on-demand in get_source() only
    // List operations return empty source_collection for performance
    const response = await api.get('/sources');
    return response.data?.data || response.data || [];
  },

  get: async (id: string): Promise<Source> => {
    const response = await api.get(`/sources/${id}`);
    return response.data;
  },

  create: async (source: Partial<Source>): Promise<Source> => {
    const response = await api.post('/sources', source);
    return response.data;
  },

  delete: async (id: string, cascade: boolean = true): Promise<void> => {
    await api.delete(`/sources/${id}`, { params: { cascade } });
  },
};

export const flowService = {
  list: async (includeStatistics?: boolean): Promise<Flow[]> => {
    const params: any = {};
    if (includeStatistics) {
      params.include_statistics = true;
    }
    const response = await api.get('/flows', { params });
    return response.data?.data || response.data || [];
  },

  getStatistics: async (): Promise<any[]> => {
    const response = await api.get('/analytics/flows');
    return response.data || [];
  },

  get: async (id: string, includeTimerange: boolean = false): Promise<Flow> => {
    const params: any = {};
    if (includeTimerange) {
      params.include_timerange = true;
    }
    const response = await api.get(`/flows/${id}`, { params });
    return response.data;
  },

  create: async (flow: Partial<Flow>): Promise<Flow> => {
    const response = await api.post('/flows', flow);
    return response.data;
  },

  update: async (id: string, flow: Partial<Flow>): Promise<Flow> => {
    const response = await api.put(`/flows/${id}`, flow);
    return response.data;
  },

  delete: async (id: string, cascade: boolean = true): Promise<void> => {
    await api.delete(`/flows/${id}`, { params: { cascade } });
  },
};

export const segmentService = {
  listByFlow: async (flowId: string, timerange?: string, limit?: number, offset?: number): Promise<Segment[]> => {
    const params: any = {};
    if (timerange) {
      params.timerange = timerange;
    }
    if (limit !== undefined) {
      params.limit = limit;
    }
    if (offset !== undefined) {
      params.offset = offset;
    }
    // Request get_urls by not setting accept_get_urls to empty string
    // The server will generate get_urls by default unless accept_get_urls="" is set
    const response = await api.get(`/flows/${flowId}/segments`, { params });
    return response.data?.data || response.data || [];
  },
};

export const objectService = {
  get: async (id: string): Promise<any> => {
    const response = await api.get(`/objects/${id}`);
    return response.data;
  },
};

export const webhookService = {
  list: async (): Promise<any[]> => {
    const response = await api.get('/service/webhooks');
    return response.data?.data || response.data || [];
  },

  create: async (webhook: any): Promise<any> => {
    const response = await api.post('/service/webhooks', webhook);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/service/webhooks/${id}`);
  },
};

export const storageBackendService = {
  list: async (): Promise<any[]> => {
    const response = await api.get('/service/storage-backends');
    return response.data?.data || response.data || [];
  },

  get: async (id: string): Promise<any> => {
    const response = await api.get(`/service/storage-backends/${id}`);
    return response.data;
  },

  create: async (backend: any): Promise<any> => {
    const response = await api.post('/service/storage-backends', backend);
    return response.data;
  },

  update: async (id: string, backend: any): Promise<any> => {
    const response = await api.put(`/service/storage-backends/${id}`, backend);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/service/storage-backends/${id}`);
  },
};

export const analyticsService = {
  getSummary: async (refresh: boolean = false): Promise<AnalyticsSummary> => {
    const params = refresh ? { refresh: 'true' } : {};
    const response = await api.get('/analytics/summary', { params });
    return response.data;
  },

  getSourceAnalytics: async (): Promise<any[]> => {
    const response = await api.get('/analytics/sources');
    return response.data || [];
  },

  getFlowAnalytics: async (): Promise<any[]> => {
    const response = await api.get('/analytics/flows');
    return response.data || [];
  },
};

export default api;

