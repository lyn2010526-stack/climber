import { useState, useMemo } from 'react';
import {
  IOSPage,
  IOSListGroup,
  IOSListItem,
  IOSSearchBar,
  IOSFab,
  IOSBadge,
  toast,
} from '../components/ios';
import { Users, Bot, Plus, Play, Pause } from 'lucide-react';
import { cn } from '../lib/utils';
import type { ReactElement } from 'react';

type CrewStatus = '运行中' | '空闲' | '停止';

interface Crew {
  id: string;
  name: string;
  icon: ReactElement;
  iconBg: string;
  members: number;
  running: boolean;
  idleStatus: CrewStatus;
}

const INITIAL_CREWS: Crew[] = [
  {
    id: '1',
    name: '开发团队',
    icon: <Users size={20} className="text-white" />,
    iconBg: '#007AFF',
    members: 4,
    running: true,
    idleStatus: '空闲',
  },
  {
    id: '2',
    name: '设计小组',
    icon: <Bot size={20} className="text-white" />,
    iconBg: '#AF52DE',
    members: 3,
    running: false,
    idleStatus: '空闲',
  },
  {
    id: '3',
    name: '数据科学',
    icon: <Users size={20} className="text-white" />,
    iconBg: '#34C759',
    members: 5,
    running: true,
    idleStatus: '空闲',
  },
  {
    id: '4',
    name: 'QA 团队',
    icon: <Bot size={20} className="text-white" />,
    iconBg: '#FF9500',
    members: 2,
    running: false,
    idleStatus: '停止',
  },
  {
    id: '5',
    name: '研究组',
    icon: <Users size={20} className="text-white" />,
    iconBg: '#5AC8FA',
    members: 4,
    running: false,
    idleStatus: '空闲',
  },
];

const statusVariant: Record<CrewStatus, 'success' | 'warning' | 'error'> = {
  运行中: 'success',
  空闲: 'warning',
  停止: 'error',
};

export default function CrewsPageIOS() {
  const [search, setSearch] = useState('');
  const [crews, setCrews] = useState<Crew[]>(INITIAL_CREWS);

  const filteredCrews = useMemo(() => {
    return crews.filter((crew) =>
      crew.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [crews, search]);

  const activeMembers = useMemo(
    () => crews.filter((c) => c.running).reduce((sum, c) => sum + c.members, 0),
    [crews]
  );

  const toggleCrew = (id: string) => {
    setCrews((prev) =>
      prev.map((crew) => {
        if (crew.id !== id) return crew;
        const running = !crew.running;
        if (running) {
          toast.success(`${crew.name} 已启动`);
        } else {
          toast.error(`${crew.name} 已暂停`);
        }
        return { ...crew, running };
      })
    );
  };

  const currentStatus = (crew: Crew): CrewStatus =>
    crew.running ? '运行中' : crew.idleStatus;

  return (
    <IOSPage className="pb-24">
      <div className="px-4 pt-6">
        <h1 className="ios-title-1 text-[var(--color-text-primary)]">Crew 协作</h1>
        <p className="ios-subhead text-[var(--color-text-muted)] mt-1">
          管理多智能体协作团队，实时掌握任务状态
        </p>
      </div>

      <div className="px-4 mt-5">
        <div className="flex gap-3">
          <div className="ios-card flex-1 p-3 text-center">
            <p className="ios-title-3 text-[var(--color-text-primary)]">
              {crews.length}
            </p>
            <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">
              Crew 总数
            </p>
          </div>
          <div className="ios-card flex-1 p-3 text-center">
            <p className="ios-title-3 text-[var(--color-success)]">
              {activeMembers}
            </p>
            <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">
              活跃成员
            </p>
          </div>
          <div className="ios-card flex-1 p-3 text-center">
            <p className="ios-title-3 text-[var(--color-warning)]">12</p>
            <p className="ios-caption text-[var(--color-text-muted)] mt-0.5">
              进行中任务
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 mt-5">
        <IOSSearchBar
          value={search}
          onChange={setSearch}
          placeholder="搜索 Crew..."
        />
      </div>

      <div className="px-4 mt-5">
        <IOSListGroup title="协作团队">
          {filteredCrews.map((crew) => {
            const status = currentStatus(crew);
            return (
              <IOSListItem
                key={crew.id}
                icon={crew.icon}
                iconBg={crew.iconBg}
                title={crew.name}
                detail={
                  <div className="flex items-center gap-2.5">
                    <div className="flex flex-col items-end gap-1">
                      <span className="ios-caption text-[var(--color-text-muted)]">
                        {crew.members} 名成员
                      </span>
                      <IOSBadge variant={statusVariant[status]}>
                        {status}
                      </IOSBadge>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleCrew(crew.id)}
                      className={cn(
                        'flex items-center justify-center w-9 h-9 rounded-full',
                        crew.running
                          ? 'bg-[var(--color-warning-subtle)] text-[var(--color-warning)]'
                          : 'bg-[var(--color-success-subtle)] text-[var(--color-success)]'
                      )}
                    >
                      {crew.running ? (
                        <Pause size={16} />
                      ) : (
                        <Play size={16} />
                      )}
                    </button>
                  </div>
                }
                showChevron={false}
              />
            );
          })}
        </IOSListGroup>
      </div>

      <IOSFab
        icon={<Plus size={20} />}
        label="创建 Crew"
        onClick={() => toast.info('创建 Crew 功能即将上线')}
      />
    </IOSPage>
  );
}
