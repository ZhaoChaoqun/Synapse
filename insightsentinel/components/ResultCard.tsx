import React from 'react';
import { SearchResult, SearchSource, Sentiment } from '../types';

interface ResultCardProps {
  result: SearchResult;
  isSelected: boolean;
  onClick: () => void;
}

const getSourceStyle = (source: SearchSource) => {
  const styles: Record<SearchSource, { bg: string; text: string; border: string; label: string }> = {
    weixin: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', label: 'WeChat' },
    zhihu: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', label: '知乎' },
    weibo: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30', label: '微博' },
    xhs: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', label: '小红书' },
    douyin: { bg: 'bg-pink-500/20', text: 'text-pink-400', border: 'border-pink-500/30', label: '抖音' },
    web: { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30', label: 'Web' },
  };
  return styles[source] || styles.web;
};

const getSentimentIcon = (sentiment?: Sentiment) => {
  switch (sentiment) {
    case 'positive': return { icon: 'sentiment_satisfied', color: 'text-green-400' };
    case 'negative': return { icon: 'sentiment_dissatisfied', color: 'text-red-400' };
    default: return { icon: 'sentiment_neutral', color: 'text-gray-400' };
  }
};

export const ResultCard: React.FC<ResultCardProps> = ({ result, isSelected, onClick }) => {
  const sourceStyle = getSourceStyle(result.source);
  const sentimentStyle = getSentimentIcon(result.sentiment);

  // Handle opening URL in new tab
  const handleOpenUrl = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    if (result.url) {
      window.open(result.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div
      onClick={onClick}
      className={`
        p-3 bg-surface-dark border rounded-lg cursor-pointer
        transition-all duration-200 group
        ${isSelected
          ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10'
          : 'border-border-dark hover:border-primary/50 hover:bg-surface-darker'
        }
      `}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {/* Header: Source badge + relevance score */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${sourceStyle.bg} ${sourceStyle.text} ${sourceStyle.border} font-medium`}>
              {sourceStyle.label}
            </span>
            <span className="text-[10px] text-text-dim font-mono">
              {result.relevanceScore}% match
            </span>
            {result.sentiment && (
              <span className={`material-symbols-outlined text-sm ${sentimentStyle.color}`}>
                {sentimentStyle.icon}
              </span>
            )}
          </div>

          {/* Title */}
          <h4 className="text-sm font-medium text-white truncate group-hover:text-primary transition-colors mb-1">
            {result.title}
          </h4>

          {/* Snippet */}
          <p className="text-xs text-text-dim line-clamp-2 leading-relaxed">
            {result.snippet}
          </p>

          {/* Footer: Author + metrics + Open link */}
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-3 text-[10px] text-gray-500">
              {result.author && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-xs">person</span>
                  {result.author}
                </span>
              )}
              {result.metrics?.views && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-xs">visibility</span>
                  {formatNumber(result.metrics.views)}
                </span>
              )}
              {result.metrics?.likes && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-xs">thumb_up</span>
                  {formatNumber(result.metrics.likes)}
                </span>
              )}
              {result.publishedAt && (
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-xs">schedule</span>
                  {formatDate(result.publishedAt)}
                </span>
              )}
            </div>

            {/* Open in new tab button */}
            {result.url ? (
              <button
                onClick={handleOpenUrl}
                className="flex items-center gap-1 text-[10px] text-primary/70 hover:text-primary transition-colors px-2 py-1 rounded hover:bg-primary/10"
                title="在新标签页打开原文"
              >
                <span className="material-symbols-outlined text-xs">open_in_new</span>
                <span className="hidden sm:inline">原文</span>
              </button>
            ) : (
              <span
                className="flex items-center gap-1 text-[10px] text-gray-600 px-2 py-1"
                title="该内容暂无可用链接"
              >
                <span className="material-symbols-outlined text-xs">link_off</span>
                <span className="hidden sm:inline">无链接</span>
              </span>
            )}
          </div>
        </div>

        {/* Chevron icon */}
        <span className="material-symbols-outlined text-text-dim group-hover:text-primary text-sm transition-colors">
          chevron_right
        </span>
      </div>
    </div>
  );
};

// Helper functions
function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return '今天';
  if (diffDays === 1) return '昨天';
  if (diffDays < 7) return `${diffDays}天前`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`;
  return `${date.getMonth() + 1}/${date.getDate()}`;
}
