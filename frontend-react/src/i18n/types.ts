// Translation namespace interface
export interface RootJson {
  common: Common;
  navigation: Navigation;
  home: Home;
  chat: Chat;
  agents: Agents;
  projects: Projects;
  settings: Settings;
  auth: Auth;
  file_manager: FileManager;
  analytics: Analytics;
  user_menu: UserMenu;
}

export interface Common {
  loading: string;
  saving: string;
  saved: string;
  cancel: string;
  confirm: string;
  delete: string;
  edit: string;
  save: string;
  add: string;
  remove: string;
  search: string;
  filter: string;
  sort: string;
  refresh: string;
  close: string;
  open: string;
  back: string;
  next: string;
  previous: string;
  done: string;
  yes: string;
  no: string;
  ok: string;
  apply: string;
  reset: string;
  clear: string;
  select: string;
  selected: string;
  all: string;
  none: string;
  custom: string;
  name: string;
  description: string;
  status: string;
  created: string;
  updated: string;
  action: string;
  actions: string;
  type: string;
  value: string;
  key: string;
  id: string;
  code: string;
  time: string;
  date: string;
  size: string;
  count: string;
  total: string;
  pages: string;
  items: string;
  language: string;
  theme: string;
  dark: string;
  light: string;
  settings: string;
  preferences: string;
  profile: string;
  account: string;
  logout: string;
  login: string;
  register: string;
  welcome: string;
  hello: string;
  goodbye: string;
  please: string;
  thanks: string;
  error: string;
  warning: string;
  success: string;
  info: string;
  message: string;
  notifications: string;
  alert: string;
  confirm_delete: string;
  confirm_cancel: string;
  loading_data: string;
  no_data: string;
  try_again: string;
  not_found: string;
  unauthorized: string;
  forbidden: string;
  server_error: string;
  network_error: string;
  timeout: string;
  invalid_input: string;
  just_now?: string;
  x_minutes_ago?: string;
  x_hours_ago?: string;
  x_days_ago?: string;
}

export interface Navigation {
  dashboard: string;
  chat: string;
  agents: string;
  projects: string;
  sessions: string;
  skills: string;
  files: string;
  analytics: string;
  docs: string;
  settings: string;
  help: string;
  support: string;
  users: string;
  teams: string;
  billing: string;
  invoices: string;
  audit: string;
  integrations: string;
  plugins: string;
  mcp: string;
  monitoring: string;
  tasks: string;
  workflows: string;
  scheduler: string;
  memory: string;
  api_keys: string;
  notifications: string;
  messages: string;
  calendar: string;
  costs: string;
  reports: string;
}

export interface Home {
  title: string;
  overview: string;
  recent_activity: string;
  quick_stats: string;
  welcome_message: string;
  active_agents: string;
  running_sessions: string;
  total_projects: string;
  daily_tasks: string;
  performance: string;
  efficiency: string;
  completion_rate: string;
  response_time: string;
  today: string;
  yesterday: string;
  this_week: string;
  this_month: string;
  last_7_days: string;
  last_30_days: string;
}

export interface Chat {
  title: string;
  placeholder: string;
  send: string;
  attach: string;
  uploading: string;
  voice_input: string;
  text_input: string;
  model_selection: string;
  context_usage: string;
  thinking_mode: string;
  execution_mode: string;
  new_chat: string;
  export_chat: string;
  clear_history: string;
  start_conversation: string;
  no_messages: string;
  typing: string;
}

export interface Agents {
  title: string;
  create_agent: string;
  agent_name: string;
  agent_type: string;
  agent_status: string;
  capabilities: string;
  resources: string;
  config: string;
  permissions: string;
  templates: string;
  copy_template: string;
  import_agent: string;
  export_agent: string;
  duplicate: string;
  clone: string;
  delete_agent: string;
  activate: string;
  deactivate: string;
  pause: string;
  resume: string;
  agent_created: string;
  agent_updated: string;
  agent_deleted: string;
}

export interface Projects {
  title: string;
  create_project: string;
  project_name: string;
  project_description: string;
  project_settings: string;
  team_members: string;
  collaborators: string;
  versions: string;
  releases: string;
  branches: string;
  commits: string;
  deployment: string;
  environment: string;
  production: string;
  staging: string;
  development: string;
  testing: string;
  private: string;
  public: string;
  archived: string;
}

export interface Settings {
  title: string;
  general: string;
  appearance: string;
  notifications: string;
  security: string;
  privacy: string;
  integrations: string;
  advanced: string;
  account_settings: string;
  password_change: string;
  email_verification: string;
  two_factor: string;
  api_settings: string;
  webhooks: string;
  data_export: string;
  account_delete: string;
  save_changes: string;
  cancel_changes: string;
  changes_saved: string;
}

export interface Auth {
  login_title: string;
  register_title: string;
  email: string;
  password: string;
  confirm_password: string;
  remember_me: string;
  forgot_password: string;
  reset_password: string;
  send_reset_link: string;
  verify_email: string;
  email_sent: string;
  email_exists: string;
  weak_password: string;
  password_mismatch: string;
  terms_accepted: string;
  privacy_policy: string;
  terms_of_service: string;
}

export interface FileManager {
  title: string;
  upload_file: string;
  drag_drop: string;
  browse_files: string;
  file_name: string;
  file_type: string;
  file_size: string;
  upload_date: string;
  delete_file: string;
  rename_file: string;
  download_file: string;
  preview_file: string;
  share_file: string;
  move_file: string;
  copy_file: string;
  new_folder: string;
  folder_name: string;
  empty_folder: string;
  search_files: string;
  no_files: string;
}

export interface Analytics {
  title: string;
  metrics: string;
  trends: string;
  comparison: string;
  real_time: string;
  historical: string;
  forecast: string;
  conversion: string;
  engagement: string;
  retention: string;
  churn: string;
  traffic: string;
  sources: string;
  devices: string;
  countries: string;
  sessions_duration: string;
  bounce_rate: string;
  page_views: string;
  unique_visitors: string;
}

export interface UserMenu {
  my_profile: string;
  edit_profile: string;
  change_avatar: string;
  notification_settings: string;
  language_settings: string;
  theme_settings: string;
  privacy_settings: string;
  security_settings: string;
  billing_info: string;
  subscription: string;
  usage_stats: string;
  api_usage: string;
  download_report: string;
  log_out: string;
}
