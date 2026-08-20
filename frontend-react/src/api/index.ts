// Barrel for the api module. Import side effects register every
// resource-domain method on the ApiClient prototype before the shared
// `api` singleton below is used by consumers.
import './agents';
import './sessions';
import './workflows';
import './groups';
import './plugins';
import './tasks';
import './traces';
import './settings';
import './permissions';
import './catalog';
import './platform';

export { api, ApiClient, BASE_URL } from './client';
export type { ApiError } from './client';
export type { ApprovalRequest, ApprovalListResponse } from './permissions';
