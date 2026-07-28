import { useState, useEffect } from 'react';
import { User } from 'lucide-react';
import { api } from '../../api';

export function UserSwitcher() {
  const [users, setUsers] = useState<Array<{ id: string; username: string; email?: string }>>([]);
  const [active, setActive] = useState<string>('default');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.listUsers().then((data) => {
      setUsers(data);
      if (data.length > 0) setActive(data[0].id);
    }).catch(() => {});
  }, []);

  const switchUser = async (userId: string) => {
    await api.switchUser({ user_id: userId });
    setActive(userId);
    setOpen(false);
  };

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-xl text-[10px] text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
      >
        <User size={10} />
        <span className="truncate">{users.find(u => u.id === active)?.username || '访客模式'}</span>
      </button>
      {open && (
        <div className="mt-1 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          {users.map((u) => (
            <button
              key={u.id}
              onClick={() => switchUser(u.id)}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-white/5 transition-colors ${
                active === u.id ? 'text-white bg-white/5' : 'text-gray-400'
              }`}
            >
              {u.username}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
