export interface User {
  user_id: string;
  username: string;
  role: 'admin' | 'editor' | 'viewer';
  password_hash?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CollectionItem {
  id: string;
  label?: string;
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
  source_collection?: CollectionItem[];
  collected_by?: string[];
}

export interface EssenceParameters {
  frame_width?: number;
  frame_height?: number;
  frame_rate?: {
    numerator?: number;
    denominator?: number;
    value?: string;
  };
  vfr?: boolean;
  sample_rate?: number;
  channels?: number;
  bit_depth?: number;
  [key: string]: any;
}

export interface Flow {
  id: string;
  label?: string;
  description?: string;
  format: string;
  source_id: string;
  codec?: string;
  container?: string;
  avg_bit_rate?: number;
  max_bit_rate?: number;
  segment_duration?: {
    numerator?: number;
    denominator?: number;
    value?: string;
  };
  essence_parameters?: EssenceParameters;
  generation?: number;
  created_by?: string;
  updated_by?: string;
  tags?: Record<string, any>;
  created?: string;
  updated?: string;
  metadata_updated?: string;
  segments_updated?: string;
}

export interface Segment {
  object_id: string;
  timerange: {
    value: string;  // TAMS format: "[start_end)" or "start_end"
  };
  ts_offset?: {
    value: string;  // Optional timestamp offset
  };
  last_duration?: {
    value: string;  // Optional last duration
  };
  sample_offset?: number;
  sample_count?: number;
  get_urls?: Array<{
    url: string;
    storage_id?: string;
    presigned?: boolean;
    label?: string;
    controlled?: boolean;
  }>;
  key_frame_count?: number;
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

export interface CountStatistics {
  total_sources: number;
  total_flows: number;
  total_segments: number;
  total_objects: number;
  flows_per_source_avg: number;
  segments_per_flow_avg: number;
}

export interface StorageStatistics {
  total_size_bytes: number;
  total_size_mb: number;
  total_size_gb: number;
  average_size_bytes: number;
  min_size_bytes: number | null;
  max_size_bytes: number | null;
  object_count_with_size: number;
}

export interface FormatBreakdown {
  video_flows: number;
  audio_flows: number;
  image_flows: number;
  data_flows: number;
  multi_flows: number;
  total_flows: number;
}

export interface TimeStatistics {
  earliest_source_created: string | null;
  latest_source_created: string | null;
  earliest_flow_created: string | null;
  latest_flow_created: string | null;
  earliest_segment_created: string | null;
  latest_segment_created: string | null;
  earliest_object_created: string | null;
  latest_object_created: string | null;
}

export interface AnalyticsSummary {
  counts: CountStatistics;
  storage: StorageStatistics;
  formats: FormatBreakdown;
  time: TimeStatistics;
  generated_at: string;
}

