import { apiClient } from '../lib/api-client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    role: string;
  };
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  role: string;
}

export const authService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/auth/login', data);
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/auth/register', data);
  },

  async logout(): Promise<void> {
    await apiClient.post<void>('/api/auth/logout', {});
  },

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/auth/refresh', { refresh_token: refreshToken });
  },

  async getProfile(): Promise<UserProfile> {
    return apiClient.get<UserProfile>('/api/auth/me');
  },

  async updateProfile(data: Record<string, unknown>): Promise<UserProfile> {
    return apiClient.put<UserProfile>('/api/auth/me', data);
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },

  async verifyEmail(token: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/api/auth/verify-email', { token });
  },

  async forgotPassword(email: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/api/auth/forgot-password', { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/api/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },
};