export interface User {
  user_id: string;
  username: string;
  role: 'admin' | 'editor' | 'viewer';
  password_hash?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Source {
  id: string;
  label?: string;
  description?: string;
  format: string;
  created_by?: string;
  updated_by?: string;
  tags?: Record<string, any>;
  created?: string;
  updated?: string;
}

export interface Flow {
  id: string;
  label?: string;
  description?: string;
  format: string;
  source_id: string;
  tags?: Record<string, any>;
  created?: string;
  updated?: string;
}

export interface Segment {
  id: string;
  flow_id: string;
  object_id: string;
  timerange: {
    start: string;
    end: string;
  };
  created?: string;
  updated?: string;
}

export interface AuthResponse {
  access_token?: string;
  token_type?: string;
  user_id: string;
  username: string;
  role: 'admin' | 'editor' | 'viewer';
}

export interface Webhook {
  id?: string;
  url: string;
  api_key_name?: string;
  api_key_value?: string;
  events?: string[];
  flow_ids?: string[];
  source_ids?: string[];
  tags?: Record<string, any>;
  enabled?: boolean;
}

export interface StorageBackend {
  id?: string;
  label: string;
  store_type: string;
  provider: string;
  store_product?: string;
  region?: string;
  availability_zone?: string;
  default_storage?: boolean;
}

