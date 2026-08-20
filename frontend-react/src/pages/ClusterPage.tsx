import { useClusterState } from '../components/cluster/useClusterState';
import { CollabConsoleView } from '../components/cluster/CollabConsoleView';
import { GroupRoomView } from '../components/cluster/GroupRoomView';
import { GroupsView } from '../components/cluster/GroupsView';
import { ClusterView } from '../components/cluster/ClusterView';

export function ClusterPage() {
  const state = useClusterState();

  // Collaboration Console View (new auto-collab mode)
  if (state.viewMode === 'collab-console' && state.activeGroupId) {
    return (
      <CollabConsoleView
        activeGroupId={state.activeGroupId}
        availableTasks={state.availableTasks}
        onLeave={state.leaveGroup}
      />
    );
  }

  // Group Room View
  if (state.viewMode === 'group-room' && state.activeGroupId) {
    return (
      <GroupRoomView
        activeGroupId={state.activeGroupId}
        onLeave={state.leaveGroup}
        onSwitchToCollab={() => state.setViewMode('collab-console')}
      />
    );
  }

  // Groups List View
  if (state.viewMode === 'groups') {
    return <GroupsView state={state} />;
  }

  // Default: Cluster View
  return <ClusterView state={state} />;
}
