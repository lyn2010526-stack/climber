export type User = {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role?: string;
  status?: string;
  avatar_url?: string;
  is_verified?: boolean;
  last_login_at?: string;
  created_at?: string;
};

export type Team = {
  id: string;
  name: string;
  description?: string;
  members?: User[];
  created_at?: string;
};

export type Ticket = {
  id: string;
  title: string;
  description?: string;
  status?: string;
  priority?: string;
  assignee_id?: string;
  created_at?: string;
};

export type Alert = {
  id: string;
  message: string;
  severity?: string;
  created_at?: string;
};

export type ApiResponse<T> = {
  data: T;
  success: boolean;
  message?: string;
};

export type PaginatedResponse<T> = {
  data: T[];
  total: number;
  page: number;
  per_page: number;
};
