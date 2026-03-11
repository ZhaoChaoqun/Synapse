import React, { useMemo } from 'react';
import { EntityGraph, Entity, EntityRelation } from '../types';

interface NetworkMapProps {
  entityGraph?: EntityGraph | null;
  isLoading?: boolean;
}

// Entity type to icon and color mapping
const ENTITY_STYLE: Record<string, { icon: string; color: string }> = {
  company: { icon: 'domain', color: 'text-blue-400' },
  product: { icon: 'smart_toy', color: 'text-secondary' },
  person: { icon: 'person', color: 'text-purple-400' },
  concept: { icon: 'lightbulb', color: 'text-yellow-400' },
  topic: { icon: 'tag', color: 'text-cyan-400' },
};

// Calculate node positions in a radial layout
function calculatePositions(entities: Entity[], centerEntityId?: string): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();

  if (entities.length === 0) return positions;

  // Find center entity or use first one
  const centerEntity = centerEntityId
    ? entities.find(e => e.id === centerEntityId) || entities[0]
    : entities[0];

  // Place center entity at 50%, 50%
  positions.set(centerEntity.id, { x: 50, y: 50 });

  // Get other entities and sort by mentions (more mentions = closer to center)
  const otherEntities = entities
    .filter(e => e.id !== centerEntity.id)
    .sort((a, b) => b.mentions - a.mentions);

  // Place entities in concentric circles
  const maxRadius = 35; // Max distance from center (in %)
  const minRadius = 20; // Min distance from center

  otherEntities.forEach((entity, index) => {
    // Calculate angle for even distribution
    const angle = (index / otherEntities.length) * 2 * Math.PI - Math.PI / 2;

    // Calculate radius based on mentions (more mentions = closer)
    const maxMentions = Math.max(...otherEntities.map(e => e.mentions), 1);
    const mentionRatio = entity.mentions / maxMentions;
    const radius = minRadius + (1 - mentionRatio) * (maxRadius - minRadius);

    // Calculate position
    const x = 50 + radius * Math.cos(angle);
    const y = 50 + radius * Math.sin(angle);

    positions.set(entity.id, { x, y });
  });

  return positions;
}

export const NetworkMap: React.FC<NetworkMapProps> = ({ entityGraph, isLoading }) => {
  // Calculate node positions
  const nodePositions = useMemo(() => {
    if (!entityGraph?.entities?.length) return new Map();
    return calculatePositions(entityGraph.entities, entityGraph.centerEntity || undefined);
  }, [entityGraph]);

  // Get entity by ID helper
  const getEntity = (id: string): Entity | undefined => {
    return entityGraph?.entities?.find(e => e.id === id);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex-1 relative overflow-hidden flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="size-16 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
          <span className="text-gray-400 text-sm">正在分析实体关系...</span>
        </div>
      </div>
    );
  }

  // Empty state - show placeholder
  if (!entityGraph || !entityGraph.entities?.length) {
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

        <div className="flex flex-col items-center gap-3 text-gray-500">
          <span className="material-symbols-outlined text-4xl opacity-50">hub</span>
          <span className="text-sm">执行任务后显示实体关系图</span>
        </div>
      </div>
    );
  }

  // Get top entities to display (limit to prevent clutter)
  const displayEntities = entityGraph.entities.slice(0, 12);
  const displayRelations = entityGraph.relations.filter(
    r => displayEntities.some(e => e.id === r.sourceId) && displayEntities.some(e => e.id === r.targetId)
  );

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
        <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none" style={{ strokeWidth: 1.5 }}>
          {displayRelations.map((relation, idx) => {
            const sourcePos = nodePositions.get(relation.sourceId);
            const targetPos = nodePositions.get(relation.targetId);
            if (!sourcePos || !targetPos) return null;

            const isOwnership = relation.relationType === 'owns';
            const strokeOpacity = 0.2 + relation.strength * 0.4;

            return (
              <g key={`${relation.sourceId}-${relation.targetId}-${idx}`}>
                <line
                  x1={`${sourcePos.x}%`}
                  y1={`${sourcePos.y}%`}
                  x2={`${targetPos.x}%`}
                  y2={`${targetPos.y}%`}
                  className={isOwnership ? 'stroke-secondary' : 'stroke-primary'}
                  style={{ strokeOpacity }}
                />
                {/* Animated flow for strong relations */}
                {relation.strength > 0.6 && (
                  <line
                    x1={`${sourcePos.x}%`}
                    y1={`${sourcePos.y}%`}
                    x2={`${targetPos.x}%`}
                    y2={`${targetPos.y}%`}
                    className="stroke-secondary"
                    strokeDasharray="5,5"
                    style={{ strokeOpacity: 0.6 }}
                  >
                    <animate
                      attributeName="stroke-dashoffset"
                      from="100"
                      to="0"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  </line>
                )}
              </g>
            );
          })}
        </svg>

        {/* Entity Nodes */}
        {displayEntities.map((entity) => {
          const pos = nodePositions.get(entity.id);
          if (!pos) return null;

          const isCenter = entity.id === entityGraph.centerEntity;
          const style = ENTITY_STYLE[entity.type] || ENTITY_STYLE.topic;

          if (isCenter) {
            // Center node (larger, with orbit animation)
            return (
              <div
                key={entity.id}
                className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer z-10"
                style={{ top: `${pos.y}%`, left: `${pos.x}%` }}
              >
                <div className="size-20 rounded-full bg-surface-dark border-4 border-primary/20 flex items-center justify-center animate-pulse-blue relative bg-opacity-80 backdrop-blur-sm">
                  <span className={`material-symbols-outlined ${style.color} text-2xl`}>
                    {style.icon}
                  </span>
                  {/* Orbiting Ring */}
                  <div
                    className="absolute w-full h-full animate-spin-slow rounded-full border border-transparent border-t-primary/60 border-r-primary/30"
                    style={{ width: '140%', height: '140%' }}
                  />
                </div>
                <div className="mt-4 bg-surface-darker/80 backdrop-blur px-3 py-1 rounded border border-primary/30 text-center max-w-[150px]">
                  <div className="text-xs font-bold text-white tracking-wide font-display truncate">
                    {entity.name}
                  </div>
                  <div className="text-[10px] text-primary font-mono uppercase">
                    {entity.type}
                  </div>
                </div>
              </div>
            );
          }

          // Regular entity node
          const nodeSize = entity.mentions > 3 ? 'size-12' : 'size-10';

          return (
            <div
              key={entity.id}
              className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer hover:scale-105 transition-transform z-10"
              style={{ top: `${pos.y}%`, left: `${pos.x}%` }}
            >
              <div
                className={`${nodeSize} rounded-full bg-surface-dark border-2 border-border-dark hover:border-primary/50 flex items-center justify-center transition-all`}
              >
                <span className={`material-symbols-outlined ${style.color} text-base`}>
                  {style.icon}
                </span>
              </div>

              <div className="mt-2 bg-surface-darker/80 px-2 py-1 rounded border border-border-dark text-[10px] text-gray-300 font-medium whitespace-nowrap flex items-center gap-1 max-w-[120px]">
                <span className="truncate">{entity.name}</span>
                {entity.mentions > 2 && (
                  <span className="text-[8px] text-primary bg-primary/10 px-1 rounded">
                    ×{entity.mentions}
                  </span>
                )}
              </div>

              {/* Tooltip on hover */}
              <div className="absolute -top-8 bg-surface-dark/90 text-gray-300 text-[9px] px-2 py-1 rounded border border-border-dark opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
                {entity.type} · 提及 {entity.mentions} 次
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="absolute bottom-2 right-2 bg-surface-darker/80 backdrop-blur px-3 py-2 rounded border border-border-dark">
        <div className="flex gap-3 text-[9px] text-gray-400">
          {Object.entries(ENTITY_STYLE).map(([type, style]) => (
            <div key={type} className="flex items-center gap-1">
              <span className={`material-symbols-outlined ${style.color} text-xs`}>
                {style.icon}
              </span>
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
