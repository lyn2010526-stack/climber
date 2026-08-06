import { Server, AlertCircle, CheckCircle, Activity, HardDrive } from 'lucide-react';
import {
  IOSPage,
  IOSCard,
  IOSListGroup,
  IOSListItem,
  IOSBadge,
} from '../components/ios';
import { cn } from '../lib/utils';

interface ClusterNode {
  name: string;
  status: 'online' | 'offline';
  cpu: number;
  memory: number;
}

const nodes: ClusterNode[] = [
  { name: 'node-alpha', status: 'online', cpu: 45, memory: 62 },
  { name: 'node-beta', status: 'online', cpu: 78, memory: 81 },
  { name: 'node-gamma', status: 'offline', cpu: 0, memory: 0 },
  { name: 'node-delta', status: 'online', cpu: 23, memory: 34 },
  { name: 'node-epsilon', status: 'online', cpu: 56, memory: 71 },
  { name: 'node-zeta', status: 'offline', cpu: 0, memory: 0 },
];

interface Resource {
  label: string;
  value: number;
  color: string;
}

const resources: Resource[] = [
  { label: '总体 CPU', value: 52, color: 'var(--color-accent)' },
];

interface ClusterEvent {
  description: string;
  time: string;
  type: 'error' | 'success';
}

const events: ClusterEvent[] = [
  { description: 'node-alpha 完成部署', time: '2 分钟前', type: 'success' },
];

export function ClusterPageIOS() {
  return (
    <IOSPage className="h-full overflow-y-auto pb-8">
      <div className="px-4 pt-6 pb-2">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">集群监控</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          实时节点状态与资源使用情况
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 px-4 py-3">
        {nodes.map((node) => (
          <IOSCard key={node.name} className="rounded-xl p-3 flex flex-col items-center text-center">
            <Server
              size={24}
              className={cn(
                'mb-2',
                node.status === 'online'
                  ? 'text-[var(--color-success)]'
                  : 'text-[var(--color-text-muted)]'
              )}
            />
            <span className="ios-caption text-[var(--color-text-primary)] font-medium truncate w-full">
              {node.name}
            </span>
            <IOSBadge
              variant={node.status === 'online' ? 'success' : 'error'}
              className="mt-1"
            >
              {node.status === 'online' ? 'online' : 'offline'}
            </IOSBadge>
            {node.status === 'online' && (
              <div className="mt-2 w-full">
                <p className="ios-caption text-[var(--color-text-muted)]">
                  CPU {node.cpu}%
                </p>
                <p className="ios-caption text-[var(--color-text-muted)]">
                  内存 {node.memory}%
                </p>
              </div>
            )}
          </IOSCard>
        ))}
      </div>

      <IOSListGroup title="资源使用" className="mb-6">
        {resources.map((res) => (
          <div key={res.label} className="ios-list-item w-full text-left px-4 py-3">
            <div className="flex items-center w-full">
              <span className="ios-list-item-icon" style={{ background: res.color }}>
                <Activity size={18} className="text-white" />
              </span>
              <span className="ios-list-item-title flex-1">{res.label}</span>
              <span className="ios-list-item-detail">
                <span className="text-[var(--color-text-muted)] ios-footnote">
                  {res.value}%
                </span>
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[var(--color-bg-surface-3)] mt-2 ml-10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${res.value}%`, background: res.color }}
              />
            </div>
          </div>
        ))}
      </IOSListGroup>

      <IOSListGroup title="最近事件" className="mb-6">
        {events.map((event, index) => (
          <IOSListItem
            key={index}
            icon={
              event.type === 'success' ? (
                <CheckCircle size={18} className="text-white" />
              ) : (
                <AlertCircle size={18} className="text-white" />
              )
            }
            iconBg={event.type === 'success' ? 'var(--color-success)' : 'var(--color-error)'}
            title={event.description}
            detail={
              <span className="text-[var(--color-text-muted)] ios-footnote">
                {event.time}
              </span>
            }
            showChevron={false}
          />
        ))}
      </IOSListGroup>
    </IOSPage>
  );
}

export default ClusterPageIOS;
