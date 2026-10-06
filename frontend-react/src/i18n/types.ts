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
  diff: Diff;
  terminal: Terminal;
  anchored: Anchored;
  apiKeys: ApiKeys;
  message: Message;
  permission_dialog: PermissionDialog;
  privacy_local_pin: PrivacyLocalPin;
  privacy_profile_learning: PrivacyProfileLearning;
  right_panel: RightPanel;
  settings_page: SettingsPage;
  sidebar: Sidebar;
  tool_call: ToolCall;
  boot: Boot;
  page_transition: PageTransition;
  hero: Hero;
  scroll: Scroll;
}

export interface Boot {
  loading: string;
  tagline: string;
}
export interface PageTransition {
  status: string;
}
export interface Hero {
  label: string;
  subtitle: string;
  cta_chat: string;
  cta_agents: string;
  cta_settings: string;
}
export interface Scroll {
  progress: { panel_label: string };
}
export interface Diff {
  title: string;
  total_lines: string;
  file_count: string;
  copy_aria: string;
  copy_title: string;
  copied: string;
  copy_failed: string;
  no_text_diff: string;
  format_unparseable: string;
  no_changes: string;
  format_hint: string;
  no_changes_hint: string;
}

export interface Terminal {
  title: string;
  read_only: string;
  executing: string;
  waiting: string;
  clear: string;
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
  card_aria_label: string;
  status_configured: string;
  status_incomplete: string;
  status_disabled: string;
  coming_soon_title: string;
  view_grid_two_col: string;
  menu_aria_label: string;
  close_form_aria_label: string;
  create_steps_aria_label: string;
  search_aria_label: string;
  loading_aria_label: string;
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
  username: string;
  login_submit: string;
  login_subtitle: string;
  invalid_credentials: string;
  login_failed: string;
  required_fields: string;
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
export interface Anchored {
  board: AnchoredBoard;
  cards: AnchoredCards;
  composer: AnchoredComposer;
  controlbar: AnchoredControlbar;
  info: AnchoredInfo;
  layout: AnchoredLayout;
  loop: AnchoredLoop;
  messages: AnchoredMessages;
  meter: AnchoredMeter;
  nav: AnchoredNav;
  panel: AnchoredPanel;
  popup: AnchoredPopup;
  preview: AnchoredPreview;
  profile: AnchoredProfile;
  queue: AnchoredQueue;
  report: AnchoredReport;
  resume: AnchoredResume;
  review: AnchoredReview;
  rules: AnchoredRules;
  start: AnchoredStart;
  status: AnchoredStatus;
  trace: AnchoredTrace;
  tree: AnchoredTree;
  welcome: AnchoredWelcome;
}

export interface AnchoredBoard {
  completed: string;
  empty: string;
  pending: string;
  running: string;
}

export interface AnchoredCards {
  file_preview: string;
  rule_editor: string;
  sub_agent_tree: string;
  task_board: string;
  token_meter: string;
}

export interface AnchoredComposer {
  attachment_failed: string;
  attachment_reading: string;
  disabled: string;
  enabled: string;
  follow_up_action: string;
  global_permission_hint: string;
  global_skills: string;
  loading: string;
  open_skills_page: string;
  pending_ack: string;
  pending_confirm: string;
  permission_settings: string;
  placeholder: string;
  reload: string;
  running_submit_hint: string;
  skill_unconfirmed: string;
  skill_update_failed: string;
  skills: string;
  skills_bad_format: string;
  skills_catalog_label: string;
  skills_empty: string;
  skills_load_failed: string;
  skills_loading: string;
  steering_action: string;
  unreported: string;
}

export interface AnchoredControlbar {
  enter_focus: string;
  exit_focus: string;
  expert: string;
  focus_shortcut: string;
  restore_named: string;
  restore_snapshot: string;
  rollback_failed: string;
  rolling_back: string;
  save_snapshot: string;
}

export interface AnchoredInfo {
  board_hint: string;
  collapse_all: string;
  expand_all: string;
  new_task: string;
  new_task_name: string;
  preview_close: string;
  reset: string;
  rule_conflict: string;
  rule_failed: string;
  rule_hint: string;
  rule_loading: string;
  rule_reload: string;
  rule_reload_conflict: string;
  rule_saving: string;
  tree_error: string;
  tree_goal: string;
  tree_result: string;
}

export interface AnchoredLayout {
  collapse_left: string;
  collapse_right: string;
  expand_left: string;
}

export interface AnchoredLoop {
  completed: string;
  current: string;
  empty: string;
  followup_queue: string;
  no_progress: string;
  queued_count: string;
  round: string;
  steering_queue: string;
  title: string;
  waiting: string;
}

export interface AnchoredMessages {
  agent_error: string;
  diff_added: string;
  diff_block: string;
  diff_removed: string;
  public_reasoning: string;
  tool_error: string;
  tool_result: string;
  tool_result_failed: string;
  tool_running: string;
  tool_success: string;
}

export interface AnchoredMeter {
  avg_turn_tokens: string;
  cache_hit_rate: string;
  cumulative_input: string;
  cumulative_output: string;
  estimated_cost: string;
  today_tokens: string;
  trend: string;
  trend_empty: string;
}

export interface AnchoredNav {
  create_default_failed: string;
  create_failed: string;
  default_title: string;
  delete_confirm: string;
  delete_failed: string;
  delete_session: string;
  label: string;
  logo_hint: string;
  logout: string;
  missing_session_id: string;
  new_session: string;
  no_matching_sessions: string;
  no_sessions: string;
  open_settings: string;
  pin: string;
  profiles: string;
  rename_session: string;
  rename_unavailable: string;
  retry_later: string;
  search_sessions: string;
  search_skills: string;
  session_menu: string;
  sessions: string;
  skills: string;
  skills_error: string;
  toggle_skill: string;
  unpin: string;
  user_unknown: string;
}

export interface AnchoredPanel {
  label: string;
}

export interface AnchoredPopup {
  approval_required: string;
  approval_title: string;
  approve: string;
  cancel: string;
  dismiss: string;
  popups_active: string;
  submit_error: string;
  submit_failed: string;
  unsupported_hint: string;
}

export interface AnchoredPreview {
  close: string;
  empty: string;
}

export interface AnchoredProfile {
  full: string;
  hint: string;
  minimal: string;
  standard: string;
}

export interface AnchoredQueue {
  kind_follow_up: string;
  kind_steering: string;
  queue: string;
  queue_pending: string;
  retry_confirm: string;
  st_applied: string;
  st_blocked: string;
  st_completed: string;
  st_failed: string;
  st_pending: string;
  st_queued: string;
  st_started: string;
  st_unconfirmed: string;
}

export interface AnchoredReport {
  completed_items: string;
  empty: string;
  report_title: string;
  risk_items: string;
  section_completed: string;
  section_executing: string;
  section_queued: string;
  section_risks: string;
}

export interface AnchoredResume {
  confirmed: string;
  failed: string;
  request_failed: string;
}

export interface AnchoredReview {
  review_check: string;
  review_confirm: string;
  review_hint: string;
  review_title: string;
  review_waiting: string;
}

export interface AnchoredRules {
  memory: string;
  project: string;
  save: string;
  soul: string;
}

export interface AnchoredStart {
  start_action: string;
  start_hint: string;
  start_title: string;
}

export interface AnchoredStatus {
  awaiting_input: string;
  cache_hit_rate: string;
  cache_percent: string;
  error: string;
  executing_tool: string;
  label: string;
  shortcuts_hint: string;
  thinking: string;
  turn_tokens: string;
  unreported: string;
}

export interface AnchoredTrace {
  detail_load_failed: string;
  detail_loading: string;
  duration_unreported: string;
  empty: string;
  epoch_changed: string;
  group_empty: string;
  group_hint: string;
  group_load_failed: string;
  group_loading: string;
  group_payload_invalid: string;
  group_pick: string;
  group_pick_account: string;
  group_tree_label: string;
  invalid_payload: string;
  kind_tasks: string;
  kind_traces: string;
  lane_done: string;
  lane_pending: string;
  lane_running: string;
  load_failed: string;
  loading: string;
  retry: string;
  retry_detail: string;
  retry_group: string;
  root_task: string;
  stream_error: string;
  stream_interrupted: string;
  stream_note: string;
  stream_retry_in: string;
  stream_retry_stopped: string;
  task_id: string;
  time_unreported: string;
  unmapped_status: string;
}

export interface AnchoredTree {
  empty: string;
}

export interface AnchoredWelcome {
  enter_hint: string;
  example_code: string;
  example_plan: string;
  example_task: string;
  shift_hint: string;
  title: string;
}

export interface ApiKeys {
  add_key: string;
  api_key_ollama_hint: string;
  api_key_optional: string;
  authApiKeys: ApiKeysAuthapikeys;
  base_url: string;
  base_url_placeholder: string;
  cancel: string;
  connection_editor: string;
  connection_map: string;
  connection_model_pending: string;
  connection_provider_derived: string;
  delete_confirm: string;
  delete_failed: string;
  delete_key_aria: string;
  deleted: string;
  empty_description: string;
  empty_title: string;
  enter_api_key: string;
  enter_name: string;
  enter_name_and_key: string;
  field_api_key: string;
  load_failed: string;
  name: string;
  name_placeholder: string;
  page_description: string;
  provider: string;
  save_failed: string;
  save_key: string;
  saved: string;
  saving: string;
  secret_saved_hint: string;
  title: string;
}

export interface ApiKeysAuthapikeys {
  close_confirm: string;
  copied_aria: string;
  copied_feedback: string;
  copy_failed: string;
  copy_hint: string;
  copy_token_aria: string;
  create: string;
  create_failed: string;
  create_key: string;
  create_new: string;
  created_feedback: string;
  created_title: string;
  creating: string;
  display_closed: string;
  empty_desc: string;
  empty_title: string;
  expires_in: string;
  expires_label: string;
  failed_load: string;
  failed_revoke: string;
  hide_token: string;
  loading: string;
  name: string;
  name_placeholder: string;
  new_token_aria: string;
  no_expiration: string;
  owner: string;
  page_description: string;
  page_title: string;
  recreate_confirm: string;
  revoke_confirm: string;
  revoke_confirm_full: string;
  revoke_key: string;
  revoked: string;
  revoked_feedback: string;
  saved_close: string;
  scopes: string;
  scopes_label: string;
  show_token: string;
  unnamed_key: string;
  valid_scope_hint: string;
}

export interface Message {
  copied: string;
  copy: string;
  edit: string;
  feedback_helpful: string;
  feedback_not_helpful: string;
  regenerate: string;
}

export interface PermissionDialog {
  action: PermissionDialogAction;
  approve: string;
  approve_all: string;
  approve_risk: string;
  confirm_risk: string;
  deny: string;
  details: string;
  expired: string;
  expired_hint: string;
  keyboard_hint: string;
  mode: PermissionDialogMode;
  retry_hint: string;
  risk: PermissionDialogRisk;
  state: PermissionDialogState;
  target: PermissionDialogTarget;
  title: string;
}

export interface PermissionDialogAction {
  command: string;
  file_delete: string;
  file_read: string;
  file_write: string;
  mcp_tool: string;
  network: string;
}

export interface PermissionDialogMode {
  acceptEdits: string;
  auto: string;
  bypass: string;
  default: string;
  plan: string;
  strict: string;
  unreported: string;
}

export interface PermissionDialogRisk {
  high: string;
  low: string;
  medium: string;
}

export interface PermissionDialogState {
  approved: string;
  approving: string;
  denied: string;
  denying: string;
  error: string;
  expired: string;
  pending: string;
  unreported: string;
}

export interface PermissionDialogTarget {
  command: string;
  path: string;
  tool: string;
  url: string;
}

export interface PrivacyLocalPin {
  action_disable: string;
  action_enable: string;
  auto_lock_off: string;
  auto_lock_seconds: string;
  cancel: string;
  disabled: string;
  enabled: string;
  error_disable_failed: string;
  error_enable_failed: string;
  error_invalid: string;
  error_mismatch: string;
  intro: string;
  label_confirm: string;
  label_current: string;
  label_set: string;
  lock_now: string;
  message_disabled: string;
  message_enabled: string;
  relock_hint: string;
  submit_disable: string;
  submit_enable: string;
  title: string;
}

export interface PrivacyProfileLearning {
  agree_label: string;
  agree_submit: string;
  cancel: string;
  closing_note: string;
  current_status: string;
  description: string;
  disable_button: string;
  enable_button: string;
  load_error: string;
  loading: string;
  message_disabled: string;
  message_enabled: string;
  reload_button: string;
  save_error: string;
  status_disabled: string;
  status_enabled: string;
  title: string;
}

export interface RightPanel {
  close: string;
  collapse_all: string;
  config: RightPanelConfig;
  expand_all: string;
  files: RightPanelFiles;
  groups: RightPanelGroups;
  sections: RightPanelSections;
  states: RightPanelStates;
  status: RightPanelStatus;
  summary: RightPanelSummary;
  title: string;
  trace: RightPanelTrace;
}

export interface RightPanelConfig {
  max_tokens: string;
  model: string;
  no_skills: string;
  no_tools: string;
  provider: string;
  skills_title: string;
  temperature: string;
  title: string;
  token_title: string;
  tokens_not_reported: string;
  tools_title: string;
}

export interface RightPanelFiles {
  chunks: string;
  chunks_other: string;
  title: string;
  title_other: string;
}

export interface RightPanelGroups {
  activity: string;
  changes: string;
  execution: string;
  overview: string;
}

export interface RightPanelSections {
  config: string;
  dag: string;
  diff: string;
  files: string;
  reasoning: string;
  toolcalls: string;
  trace: string;
}

export interface RightPanelStates {
  empty_dag: string;
  empty_dag_hint: string;
  empty_diff: string;
  empty_diff_hint: string;
  empty_documents: string;
  empty_documents_hint: string;
  empty_tools: string;
  empty_tools_hint: string;
  empty_trace: string;
  empty_trace_hint: string;
  load_failed: string;
  load_failed_hint: string;
  loading: string;
  retry: string;
}

export interface RightPanelStatus {
  completed: string;
  error: string;
  failed: string;
  idle: string;
  paused: string;
  pending: string;
  running: string;
  stopped: string;
  unknown: string;
}

export interface RightPanelSummary {
  no_session: string;
  no_session_hint: string;
  none: string;
  not_reported: string;
  token_of_limit: string;
  tokens: string;
  untitled: string;
}

export interface RightPanelTrace {
  duration: string;
  tokens: string;
}

export interface SettingsPage {
  account_load_failed: string;
  account_update_unsupported: string;
  api_docs: string;
  auth_disabled: string;
  auth_enabled: string;
  auth_method: string;
  auth_none: string;
  auth_status: string;
  auth_status_desc: string;
  auto_agent: string;
  auto_agent_desc: string;
  auto_saved: string;
  available: string;
  available_models: string;
  available_models_desc: string;
  basic_title: string;
  change_pwd: string;
  clear_webhook_confirm: string;
  config_saved: string;
  confirm_btn: string;
  confirm_pwd: string;
  confirm_pwd_ph: string;
  current_pwd: string;
  current_pwd_ph: string;
  email: string;
  email_desc: string;
  email_marketing: string;
  email_marketing_desc: string;
  email_notif: string;
  email_placeholder: string;
  email_system: string;
  email_system_desc: string;
  email_task_done_desc: string;
  email_task_done_label: string;
  email_weekly: string;
  email_weekly_desc: string;
  execution_mode: string;
  github_repo: string;
  help_docs: string;
  loading_models: string;
  mcp_not_ready: string;
  mcp_ready: string;
  mcp_status: string;
  mcp_throttle: string;
  mcp_throttle_desc: string;
  model_load_failed: string;
  new_pwd: string;
  new_pwd_ph: string;
  no_link: string;
  no_models: string;
  notif_email: string;
  notif_email_desc: string;
  notif_load_failed: string;
  notif_missing: string;
  notif_save_failed: string;
  perm_update_failed: string;
  pwd_change_failed: string;
  pwd_change_hint: string;
  pwd_changed: string;
  pwd_desc: string;
  pwd_label: string;
  pwd_mismatch: string;
  pwd_reuse: string;
  pwd_title: string;
  pwd_too_short: string;
  related_links: string;
  reload: string;
  reload_confirm: string;
  retry: string;
  role: string;
  role_desc: string;
  saved: string;
  saving: string;
  security_load_failed: string;
  settings_load_failed: string;
  settings_update_failed: string;
  trigger_events: string;
  username: string;
  username_desc: string;
  username_placeholder: string;
  version: string;
  version_unreported: string;
  version_unset: string;
  webhook_clear: string;
  webhook_keep: string;
  webhook_placeholder_configured: string;
  webhook_state_clear: string;
  webhook_state_configured: string;
  webhook_state_not: string;
  webhook_task_done: string;
  webhook_task_done_desc: string;
  webhook_task_failed: string;
  webhook_task_failed_desc: string;
  webhook_title: string;
  webhook_url: string;
  webhook_url_desc: string;
}

export interface Sidebar {
  all_entries: string;
  close_menu: string;
  collapse: string;
  command_menu: string;
  expand: string;
  global_search: string;
  hint: string;
  main_nav: string;
  more: string;
  open_menu: string;
  session: SidebarSession;
  workspace: string;
}

export interface SidebarSession {
  agents_empty: string;
  agents_load_failed: string;
  agents_unreported: string;
  all_status: string;
  cancel: string;
  checkpoint_history: string;
  clear_filter: string;
  create: string;
  create_config: string;
  create_failed: string;
  creating: string;
  delete: string;
  delete_body: string;
  delete_failed: string;
  delete_title: string;
  filter_off: string;
  filter_on: string;
  filter_status: string;
  identity_changed: string;
  identity_error: string;
  model_credential: string;
  model_default: string;
  model_source: string;
  no_checkpoints: string;
  no_match_count: string;
  no_match_title: string;
  pick_agent: string;
  search_placeholder: string;
  search_title: string;
  session_n: string;
  sessions_load_failed: string;
  sessions_unreported: string;
}

export interface ToolCall {
  arguments: string;
  auto_expand: string;
  collapse: string;
  collapse_all: string;
  copied: string;
  copy: string;
  copy_failed: string;
  error_detail: string;
  expand: string;
  expand_all: string;
  output_empty: string;
  result: string;
  running_count: string;
  running_count_one: string;
  running_count_other: string;
  show_all: string;
  show_all_one: string;
  show_all_other: string;
  show_less: string;
  status_awaiting_approval: string;
  status_cancelled: string;
  status_error: string;
  status_pending: string;
  status_running: string;
  status_success: string;
  status_unknown: string;
  summary: string;
  summary_one: string;
  summary_other: string;
  summary_running: string;
  thinking_chars: string;
  thinking_chars_one: string;
  thinking_chars_other: string;
}
