const WORKSPACE_ENTRY_STORAGE_KEY = 'climber.workspace.enter.v1';

/**
 * Whether the three-rail arrival has already been spent in this tab.
 *
 * Its own flag rather than the boot one: the workspace is mounted underneath
 * the splash from the first frame, so it has to decide before the splash has
 * marked the boot session, and it has to stay decided across a route change
 * that remounts the layout without a reload.
 */
export function hasPlayedWorkspaceEntry(): boolean {
  try {
    return window.sessionStorage.getItem(WORKSPACE_ENTRY_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export function markWorkspaceEntryPlayed(): void {
  try {
    window.sessionStorage.setItem(WORKSPACE_ENTRY_STORAGE_KEY, '1');
  } catch {
    return;
  }
}

export function resetWorkspaceEntryForTests(): void {
  try {
    window.sessionStorage.removeItem(WORKSPACE_ENTRY_STORAGE_KEY);
  } catch {
    return;
  }
}
