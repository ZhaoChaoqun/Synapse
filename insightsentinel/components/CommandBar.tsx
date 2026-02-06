import React, { useState } from 'react';

interface CommandBarProps {
  onExecute: (command: string) => void;
  isProcessing: boolean;
  onAbort?: () => void;
}

export const CommandBar: React.FC<CommandBarProps> = ({ onExecute, isProcessing, onAbort }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      onExecute(input);
      setInput('');
    }
  };

  const quickActions = [
    { icon: 'psychology', label: 'Analyze Sentiment', color: 'text-purple-400' },
    { icon: 'hub', label: 'Map Connections', color: 'text-green-400' },
    { icon: 'warning', label: 'Risk Assess', color: 'text-orange-400' },
  ];

  return (
    <div className="p-6 relative z-20 shrink-0">
      <div className="max-w-4xl mx-auto bg-surface-dark/80 backdrop-blur-md border border-border-dark rounded-xl shadow-2xl overflow-hidden flex flex-col relative group focus-within:border-primary/50 transition-colors">
        
        {/* Input Area */}
        <form onSubmit={handleSubmit} className="flex items-center p-4 gap-4">
          <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <span className={`material-symbols-outlined text-primary ${isProcessing ? 'animate-spin' : 'animate-pulse'}`}>
              {isProcessing ? 'sync' : 'terminal'}
            </span>
          </div>
          
          <div className="flex-1 flex flex-col justify-center">
            <label htmlFor="agent-command" className="sr-only">Command</label>
            <div className="flex items-center text-lg font-mono text-white">
              <span className="text-primary mr-2">&gt;</span>
              <input 
                id="agent-command" 
                type="text" 
                autoComplete="off"
                className="bg-transparent border-none outline-none w-full placeholder-gray-600 font-mono focus:ring-0 p-0"
                placeholder="Monitor updates on [Agentic Workflow]..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isProcessing}
              />
            </div>
          </div>

          {isProcessing && onAbort ? (
            <button
              type="button"
              onClick={onAbort}
              className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg text-sm font-bold tracking-wide transition-colors flex items-center gap-2"
            >
              ABORT
              <span className="material-symbols-outlined text-sm">close</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={isProcessing || !input.trim()}
              className={`bg-primary hover:bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-bold tracking-wide transition-colors flex items-center gap-2 ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isProcessing ? 'PROCESSING' : 'EXECUTE'}
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </button>
          )}
        </form>

        {/* Quick Actions */}
        <div className="bg-surface-darker/50 px-4 py-3 flex items-center gap-3 border-t border-border-dark overflow-x-auto">
          <span className="text-[10px] font-bold text-text-dim uppercase tracking-wider shrink-0">Quick Actions:</span>
          {quickActions.map((action, i) => (
            <button 
              key={i}
              onClick={() => onExecute(action.label)}
              disabled={isProcessing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-dark border border-border-dark hover:border-primary/40 hover:bg-primary/5 transition-all group shrink-0"
            >
              <span className={`material-symbols-outlined ${action.color} text-[16px]`}>{action.icon}</span>
              <span className="text-xs text-gray-300 group-hover:text-white">{action.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};