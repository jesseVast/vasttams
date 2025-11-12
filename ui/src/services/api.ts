import axios from 'axios';
import { User, Source, Flow, Segment, AuthResponse, AnalyticsSummary, StorageBackend } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

// Logout and redirect on auth failures
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const path = window.location.pathname;
    const isAuthRoute = path.toLowerCase().includes('/login');

    // Treat 401/403 as invalid/expired token
    if ((status === 401 || status === 403) && !isAuthRoute) {
      try {
        // Clear stored auth
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      } catch {}
      // Redirect to login
      window.location.replace('/login');
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
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  getCurrentUser: (): User | null => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
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

  delete: async (id: string): Promise<void> => {
    await api.delete(`/sources/${id}`);
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

  delete: async (id: string): Promise<void> => {
    await api.delete(`/flows/${id}`);
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
    const response = await api.get(`/flows/${flowId}/segments`, { params });
    return response.data?.data || response.data || [];
  },
};

// HLS service removed - UI no longer uses HLS endpoints
// export const hlsService = {
//   getStatus: async (flowId: string): Promise<{ hls_ready: boolean; segment_count?: number; reason?: string; playlist_url?: string }> => {
//     const response = await api.get(`/hls/flows/${flowId}/status`);
//     return response.data;
//   },
//   getPlaylistUrl: (flowId: string): string => {
//     const baseUrl = API_BASE_URL.replace(/\/$/, ''); // Remove trailing slash
//     const token = localStorage.getItem('token');
//     // Add token as query parameter for HLS players that can't send headers
//     if (token) {
//       return `${baseUrl}/hls/flows/${flowId}/playlist.m3u8?access_token=${encodeURIComponent(token)}`;
//     }
//     return `${baseUrl}/hls/flows/${flowId}/playlist.m3u8`;
//   },
// };

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
  getSummary: async (): Promise<AnalyticsSummary> => {
    const response = await api.get('/analytics/summary');
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

