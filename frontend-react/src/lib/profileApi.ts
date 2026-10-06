import { api } from '../api';
import type { ProfileSettingsUpdate } from '../api';

export type { ProfileSettings, ProfileSettingsUpdate } from '../api';

export const profileApi = {
  getSettings: (signal?: AbortSignal) => api.getProfileSettings(signal),
  updateSettings: (settings: ProfileSettingsUpdate) => api.putProfileSettings(settings),
};
