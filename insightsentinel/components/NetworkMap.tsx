import React from 'react';
import { NetworkNode } from '../types';

export const NetworkMap: React.FC = () => {
  // Hardcoded nodes for the visual demo
  const nodes: NetworkNode[] = [
    { id: 'core', label: 'INSIGHT CORE', type: 'core', x: 50, y: 50, status: 'active' },
    { id: 'n1', label: 'DeepSeek', type: 'node', x: 25, y: 30, status: 'velocity', icon: 'smart_toy', color: 'text-blue-400' },
    { id: 'n2', label: 'Moonshot AI', type: 'node', x: 75, y: 25, status: 'active', icon: 'rocket_launch', color: 'text-secondary' },
    { id: 'n3', label: 'KOL: TechBrother', type: 'kol', x: 35, y: 70, status: 'normal', icon: 'person', color: 'text-purple-400' },
    { id: 'n4', label: 'Alibaba Cloud', type: 'cloud', x: 80, y: 60, status: 'normal', icon: 'cloud', color: 'text-orange-400' },
  ];

  return (
    <div className="flex-1 relative overflow-hidden flex items-center justify-center">
      {/* Background Grid & Gradient */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1000 600" preserveAspectRatio="none">
          <defs>
            <radialGradient id="grad1" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
              <stop offset="0%" style={{ stopColor: 'rgba(19, 127, 236, 0.1)', stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: 'rgba(19, 127, 236, 0)', stopOpacity: 0 }} />
            </radialGradient>
          </defs>
          <circle cx="500" cy="300" r="400" fill="url(#grad1)" />
        </svg>
      </div>

      {/* Map Container */}
      <div className="relative w-full h-full max-w-5xl max-h-[600px] mx-auto z-0">
        
        {/* SVG Connections */}
        <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none stroke-border-dark" style={{ strokeWidth: 1.5 }}>
          {/* Static lines from core to others */}
          <line x1="50%" y1="50%" x2="25%" y2="30%" className="stroke-primary/30" />
          <line x1="50%" y1="50%" x2="75%" y2="25%" className="stroke-primary/30" />
          <line x1="50%" y1="50%" x2="35%" y2="70%" className="stroke-primary/30" />
          <line x1="50%" y1="50%" x2="80%" y2="60%" className="stroke-primary/30" />
          
          {/* Active Data Flow Line (Animated) */}
          <line x1="50%" y1="50%" x2="75%" y2="25%" className="stroke-secondary" strokeDasharray="5,5">
            <animate attributeName="stroke-dashoffset" from="100" to="0" dur="2s" repeatCount="indefinite" />
          </line>
        </svg>

        {/* Nodes */}
        {nodes.map((node) => {
          if (node.type === 'core') {
            return (
              <div 
                key={node.id}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer z-10"
              >
                <div className="size-20 rounded-full bg-surface-dark border-4 border-primary/20 flex items-center justify-center animate-pulse-blue relative bg-opacity-80 backdrop-blur-sm">
                  <div className="size-3 rounded-full bg-primary shadow-[0_0_15px_rgba(19,127,236,1)]"></div>
                  {/* Orbiting Ring */}
                  <div 
                    className="absolute w-full h-full animate-spin-slow rounded-full border border-transparent border-t-primary/60 border-r-primary/30" 
                    style={{ width: '140%', height: '140%' }}
                  ></div>
                </div>
                <div className="mt-4 bg-surface-darker/80 backdrop-blur px-3 py-1 rounded border border-primary/30 text-center">
                  <div className="text-xs font-bold text-white tracking-widest font-display">INSIGHT CORE</div>
                  <div className="text-[10px] text-primary font-mono">GCR REGION</div>
                </div>
              </div>
            );
          }

          return (
            <div 
              key={node.id}
              className={`absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer hover:scale-105 transition-transform z-10`}
              style={{ top: `${node.y}%`, left: `${node.x}%` }}
            >
              <div className={`
                size-${node.type === 'kol' ? '10' : '12'} 
                rounded-full bg-surface-dark border-2 
                ${node.status === 'active' ? 'border-secondary/50 shadow-[0_0_10px_rgba(0,255,157,0.2)]' : 'border-border-dark hover:border-blue-400'} 
                flex items-center justify-center transition-all
              `}>
                <span className={`material-symbols-outlined ${node.color} ${node.type === 'kol' ? 'text-sm' : 'text-base'}`}>
                  {node.icon}
                </span>
                
                {node.type === 'kol' && (
                  <div className="absolute -right-1 -top-1 size-3 bg-blue-500 rounded-full border-2 border-surface-dark flex items-center justify-center">
                     <span className="material-symbols-outlined text-white text-[8px]">check</span>
                  </div>
                )}
              </div>
              
              <div className="mt-2 bg-surface-darker/80 px-2 py-1 rounded border border-border-dark text-[10px] text-gray-300 font-medium whitespace-nowrap flex items-center gap-1">
                {node.label}
                {node.status === 'active' && <div className="size-1.5 bg-secondary rounded-full animate-pulse"></div>}
              </div>

              {node.status === 'velocity' && (
                 <div className="absolute -top-6 bg-red-500/10 text-red-400 text-[9px] px-1.5 rounded border border-red-500/20 opacity-0 group-hover:opacity-100 transition-opacity">
                    Velocity +15%
                 </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};