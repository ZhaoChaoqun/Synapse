import React, { useEffect, useRef, useState } from 'react';
import { LogEntry, LogLevel } from '../types';

interface LogPanelProps {
  logs: LogEntry[];
}

const LogItem: React.FC<{ log: LogEntry }> = ({ log }) => {
  const [showScreenshot, setShowScreenshot] = useState(true);

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
        {log.screenshot && (
          <button
            onClick={() => setShowScreenshot(!showScreenshot)}
            className="text-[10px] px-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
          >
            {showScreenshot ? '隐藏截图' : '显示截图'}
          </button>
        )}
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
      {log.screenshot && showScreenshot && (
        <div className="mt-2 relative group">
          <img
            src={`data:image/jpeg;base64,${log.screenshot}`}
            alt="Browser screenshot"
            className="w-full rounded border border-cyan-500/30 shadow-lg shadow-cyan-500/10 cursor-pointer hover:border-cyan-400/50 transition-colors"
            onClick={() => {
              // Open in new tab for full view
              const newTab = window.open();
              if (newTab) {
                newTab.document.body.innerHTML = `<img src="data:image/jpeg;base64,${log.screenshot}" style="max-width: 100%; height: auto;" />`;
                newTab.document.body.style.backgroundColor = '#0a0a0f';
                newTab.document.body.style.margin = '0';
                newTab.document.body.style.display = 'flex';
                newTab.document.body.style.justifyContent = 'center';
                newTab.document.body.style.alignItems = 'center';
                newTab.document.body.style.minHeight = '100vh';
              }
            }}
          />
          <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] bg-black/70 px-2 py-1 rounded text-cyan-400">
              点击放大
            </span>
          </div>
        </div>
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