import React, { useEffect, useRef } from 'react';
import { LogEntry, LogLevel } from '../types';

interface LogPanelProps {
  logs: LogEntry[];
}

const LogItem: React.FC<{ log: LogEntry }> = ({ log }) => {
  const getColors = (level: LogLevel) => {
    switch (level) {
      case LogLevel.INFO: return { text: 'text-primary', bg: 'bg-primary/20', border: 'border-primary/50' };
      case LogLevel.WARN: return { text: 'text-yellow-500', bg: 'bg-yellow-500/20', border: 'border-yellow-500/50' };
      case LogLevel.ALERT: return { text: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/50' };
      case LogLevel.EXEC: return { text: 'text-secondary', bg: 'bg-secondary/20', border: 'border-secondary' };
      case LogLevel.NET: return { text: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-border-dark' };
      case LogLevel.DEBUG: return { text: 'text-gray-400', bg: 'bg-gray-700/50', border: 'border-border-dark' };
      default: return { text: 'text-gray-300', bg: 'bg-gray-800', border: 'border-gray-700' };
    }
  };

  const colors = getColors(log.level);
  const isExec = log.level === LogLevel.EXEC;

  return (
    <div className={`flex flex-col gap-1 border-l-2 pl-3 ${colors.border} ${isExec ? 'bg-secondary/5 rounded-r p-2 -ml-2' : ''} mb-4 animate-in fade-in slide-in-from-left-2 duration-300`}>
      <div className={`flex items-center gap-2 mb-1 ${isExec ? 'text-secondary' : 'text-text-dim'}`}>
        <span className="opacity-50 font-mono text-[10px]">{log.timestamp}</span>
        <span className={`text-[10px] px-1 rounded font-bold ${colors.bg} ${colors.text}`}>
          {log.level}
        </span>
      </div>
      <p className={`${isExec ? 'text-white' : 'text-gray-300'} leading-relaxed text-xs font-mono`}>
        {log.message}
      </p>
      {log.progress !== undefined && (
        <div className="mt-1 w-full bg-gray-800 rounded-full h-1 overflow-hidden">
          <div className="bg-secondary h-full transition-all duration-1000" style={{ width: `${log.progress}%` }}></div>
        </div>
      )}
      {log.details && (
        <p className="text-[10px] text-gray-500 font-mono mt-0.5">{log.details}</p>
      )}
    </div>
  );
};

export const LogPanel: React.FC<LogPanelProps> = ({ logs }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <aside className="w-80 bg-surface-darker border-r border-border-dark flex flex-col shrink-0 z-10 h-full">
      <div className="p-4 border-b border-border-dark flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-widest text-text-dim flex items-center gap-2 font-display">
          <span className="material-symbols-outlined text-primary text-sm">terminal</span>
          Live Reasoning
        </h2>
        <div className="flex gap-1">
          <div className="size-2 rounded-full bg-red-500/20 border border-red-500/50"></div>
          <div className="size-2 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
          <div className="size-2 rounded-full bg-green-500/20 border border-green-500/50"></div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {logs.map((log) => (
          <LogItem key={log.id} log={log} />
        ))}
        <div ref={endRef} />
      </div>

      <div className="p-3 border-t border-border-dark bg-surface-darker">
        <div className="flex items-center gap-2 text-xs font-mono text-text-dim">
          <span className="text-secondary">root@sentinel:~#</span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </aside>
  );
};