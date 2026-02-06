import React from 'react';
import { MetricCard } from '../types';

const Card: React.FC<{ data: MetricCard }> = ({ data }) => {
  const getTheme = (color: string) => {
    switch(color) {
      case 'green': return { text: 'text-green-500', sub: 'text-green-400', bg: 'bg-green-500/5', stroke: 'text-green-500' };
      case 'blue': return { text: 'text-blue-500', sub: 'text-blue-400', bg: 'bg-blue-500/5', stroke: 'text-blue-500' };
      case 'red': return { text: 'text-red-500', sub: 'text-red-400', bg: 'bg-red-500/5', stroke: 'text-red-500' };
      default: return { text: 'text-white', sub: 'text-white', bg: 'bg-gray-100/5', stroke: 'text-white' };
    }
  };

  const theme = getTheme(data.colorTheme);

  return (
    <div className="bg-surface-dark border border-border-dark rounded-xl p-4 flex flex-col gap-3 relative overflow-hidden group hover:border-primary/50 transition-colors">
      <div className={`absolute top-0 right-0 w-20 h-20 ${theme.bg} rounded-bl-full -mr-10 -mt-10`}></div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`material-symbols-outlined ${theme.text}`}>{data.icon}</span>
          <span className="font-bold text-sm font-display">{data.platform}</span>
        </div>
        <span className={`text-xs font-mono ${theme.sub} flex items-center gap-1`}>
          <span className="material-symbols-outlined text-[14px]">
            {data.trendUp ? 'arrow_upward' : 'arrow_downward'}
          </span> 
          {data.trend}%
        </span>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <div className="text-3xl font-bold tracking-tight font-display">
            {data.score}<span className="text-sm text-text-dim font-normal">/100</span>
          </div>
          <div className="text-[10px] text-text-dim uppercase tracking-wider mt-1 font-mono">Hotness Score</div>
        </div>
        
        {/* Circular Progress SVG */}
        <div className="h-10 w-10 relative flex items-center justify-center">
          <svg viewBox="0 0 36 36" className="transform -rotate-90 w-full h-full">
            <path className="text-gray-700" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="4" />
            <path className={theme.stroke} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${data.score}, 100`} strokeWidth="4" />
          </svg>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-border-dark space-y-1">
        {data.tags.map((tag, i) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="text-text-dim">{tag.label}</span>
            <span className="text-white font-mono">{tag.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const StatsGrid: React.FC = () => {
  const cards: MetricCard[] = [
    {
      id: '1', platform: 'WeChat Pulse', icon: 'chat', iconColor: 'text-green-500',
      trend: 12, trendUp: true, score: 88, colorTheme: 'green',
      tags: [{ label: '#AIRegulation', count: '2.4M' }, { label: '#LLM', count: '1.1M' }]
    },
    {
      id: '2', platform: 'Zhihu Heat', icon: 'school', iconColor: 'text-blue-500',
      trend: 5, trendUp: true, score: 76, colorTheme: 'blue',
      tags: [{ label: '#DeepSeek', count: '890K' }, { label: '#AGI', count: '450K' }]
    },
    {
      id: '3', platform: 'XHS Trend', icon: 'favorite', iconColor: 'text-red-500',
      trend: 3, trendUp: false, score: 92, colorTheme: 'red',
      tags: [{ label: '#AICovers', count: '3.2M' }, { label: '#DigitalHuman', count: '1.8M' }]
    },
    {
      id: '4', platform: 'Douyin Vel', icon: 'music_note', iconColor: 'text-white',
      trend: 8, trendUp: true, score: 65, colorTheme: 'white',
      tags: [{ label: '#AgenticWorkflow', count: '560K' }, { label: '#TechTok', count: '1.2M' }]
    }
  ];

  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 z-10">
      {cards.map(card => <Card key={card.id} data={card} />)}
    </div>
  );
};