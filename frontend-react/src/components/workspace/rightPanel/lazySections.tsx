import { lazy } from 'react';

/**
 * Every section module is a separate chunk.
 *
 * The panel is an on-demand tool, so its body is loaded the way it is displayed:
 * a chunk is requested only once its group is open, and a section nobody opens
 * costs no request at all. Sections that share a module stay in one chunk,
 * matching how they ship together.
 */
export const ConfigSection = lazy(() =>
  import('./sections/ConfigSection').then((module) => ({ default: module.ConfigSection })),
);

export const DagSection = lazy(() =>
  import('./sections/ExecutionSection').then((module) => ({ default: module.DagSection })),
);

export const TraceSection = lazy(() =>
  import('./sections/ExecutionSection').then((module) => ({ default: module.TraceSection })),
);

export const DiffSection = lazy(() =>
  import('./sections/ChangesSection').then((module) => ({ default: module.DiffSection })),
);

export const FilesSection = lazy(() =>
  import('./sections/ChangesSection').then((module) => ({ default: module.FilesSection })),
);

export const ActivitySection = lazy(() =>
  import('./sections/ActivitySection').then((module) => ({ default: module.ActivitySection })),
);
