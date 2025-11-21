import axios from 'axios';
import { User, Source, Flow, Segment, AuthResponse, AnalyticsSummary } from '../types';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const API_PREFIX = '/api/tams/v8.0';

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
      const response = await api.post(`${API_PREFIX}/auth/login`, {
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
    const response = await api.get(`${API_PREFIX}/users`);
    return response.data || [];
  },

  create: async (username: string, role: string, password: string): Promise<User> => {
    const response = await api.post(`${API_PREFIX}/users`, {
      username,
      password,
      role,
    });
    return response.data;
  },

  delete: async (username: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/users/${username}`);
  },

  updateRole: async (username: string, role: string): Promise<void> => {
    await api.put(`${API_PREFIX}/users/${username}/role`, { role });
  },

  updatePassword: async (username: string, password: string): Promise<void> => {
    await api.put(`${API_PREFIX}/users/${username}/password`, { password });
  },
};

export const sourceService = {
  list: async (): Promise<Source[]> => {
    // source_collection is computed on-demand in get_source() only
    // List operations return empty source_collection for performance
    const response = await api.get(`${API_PREFIX}/sources`);
    return response.data?.data || response.data || [];
  },

  get: async (id: string): Promise<Source> => {
    const response = await api.get(`${API_PREFIX}/sources/${id}`);
    return response.data;
  },

  create: async (source: Partial<Source>): Promise<Source> => {
    const response = await api.post(`${API_PREFIX}/sources`, source);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/sources/${id}`);
  },
};

export const flowService = {
  list: async (includeStatistics?: boolean): Promise<Flow[]> => {
    const params: any = {};
    if (includeStatistics) {
      params.include_statistics = true;
    }
    const response = await api.get(`${API_PREFIX}/flows`, { params });
    return response.data?.data || response.data || [];
  },

  getStatistics: async (): Promise<any[]> => {
    const response = await api.get(`${API_PREFIX}/analytics/flows`);
    return response.data || [];
  },

  get: async (id: string, includeTimerange: boolean = false): Promise<Flow> => {
    const params: any = {};
    if (includeTimerange) {
      params.include_timerange = true;
    }
    const response = await api.get(`${API_PREFIX}/flows/${id}`, { params });
    return response.data;
  },

  create: async (flow: Partial<Flow>): Promise<Flow> => {
    const response = await api.post(`${API_PREFIX}/flows`, flow);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/flows/${id}`);
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
    const response = await api.get(`${API_PREFIX}/flows/${flowId}/segments`, { params });
    return response.data?.data || response.data || [];
  },
};

export const webhookService = {
  list: async (): Promise<any[]> => {
    const response = await api.get(`${API_PREFIX}/service/webhooks`);
    return response.data?.data || response.data || [];
  },

  create: async (webhook: any): Promise<any> => {
    const response = await api.post(`${API_PREFIX}/service/webhooks`, webhook);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/service/webhooks/${id}`);
  },
};

export const storageBackendService = {
  list: async (): Promise<any[]> => {
    const response = await api.get(`${API_PREFIX}/service/storage-backends`);
    return response.data?.data || response.data || [];
  },

  get: async (id: string): Promise<any> => {
    const response = await api.get(`${API_PREFIX}/service/storage-backends/${id}`);
    return response.data;
  },

  create: async (backend: any): Promise<any> => {
    const response = await api.post(`${API_PREFIX}/service/storage-backends`, backend);
    return response.data;
  },

  update: async (id: string, backend: any): Promise<any> => {
    const response = await api.put(`${API_PREFIX}/service/storage-backends/${id}`, backend);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`${API_PREFIX}/service/storage-backends/${id}`);
  },
};

export const analyticsService = {
  getSummary: async (refresh: boolean = false): Promise<AnalyticsSummary> => {
    const params = refresh ? { refresh: 'true' } : {};
    const response = await api.get(`${API_PREFIX}/analytics/summary`, { params });
    return response.data;
  },

  getSourceAnalytics: async (): Promise<any[]> => {
    const response = await api.get(`${API_PREFIX}/analytics/sources`);
    return response.data || [];
  },

  getFlowAnalytics: async (): Promise<any[]> => {
    const response = await api.get(`${API_PREFIX}/analytics/flows`);
    return response.data || [];
  },
};

export default api;

