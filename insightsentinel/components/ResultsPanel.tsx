import React, { useState } from 'react';
import { SearchResult, SearchSource, Sentiment } from '../types';
import { ResultCard } from './ResultCard';

interface ResultsPanelProps {
  results: SearchResult[];
  totalCount: number;
  isLoading: boolean;
  selectedId: string | null;
  onSelectResult: (id: string) => void;
  onClose: () => void;
}

// Result detail view component
const ResultDetail: React.FC<{
  result: SearchResult;
  onClose: () => void;
}> = ({ result, onClose }) => {
  const getSourceLabel = (source: SearchSource) => {
    const labels: Record<SearchSource, string> = {
      weixin: 'WeChat 公众号',
      zhihu: '知乎',
      weibo: '微博',
      xhs: '小红书',
      douyin: '抖音',
      web: '网页',
    };
    return labels[source] || source;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border-dark flex items-center justify-between">
        <button
          onClick={onClose}
          className="flex items-center gap-1 text-text-dim hover:text-white transition-colors text-sm"
        >
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          返回列表
        </button>
        {result.url ? (
          <a
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors text-sm"
          >
            <span className="material-symbols-outlined text-sm">open_in_new</span>
            查看原文
          </a>
        ) : (
          <span className="flex items-center gap-1 text-gray-500 text-sm" title="该内容暂无可用链接">
            <span className="material-symbols-outlined text-sm">link_off</span>
            暂无链接
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {/* Title */}
        <h3 className="text-lg font-medium text-white mb-3 leading-relaxed">
          {result.title}
        </h3>

        {/* Meta info */}
        <div className="flex flex-wrap items-center gap-3 mb-4 text-xs text-text-dim">
          <span className="px-2 py-1 rounded bg-primary/20 text-primary border border-primary/30">
            {getSourceLabel(result.source)}
          </span>
          {result.author && (
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">person</span>
              {result.author}
            </span>
          )}
          {result.publishedAt && (
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">calendar_today</span>
              {new Date(result.publishedAt).toLocaleDateString('zh-CN')}
            </span>
          )}
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">analytics</span>
            相关度 {result.relevanceScore}%
          </span>
        </div>

        {/* Metrics */}
        {result.metrics && (
          <div className="flex gap-4 mb-4 p-3 bg-surface-dark rounded-lg border border-border-dark">
            {result.metrics.views !== undefined && (
              <div className="text-center">
                <div className="text-lg font-bold text-white">{formatMetric(result.metrics.views)}</div>
                <div className="text-[10px] text-text-dim">阅读</div>
              </div>
            )}
            {result.metrics.likes !== undefined && (
              <div className="text-center">
                <div className="text-lg font-bold text-primary">{formatMetric(result.metrics.likes)}</div>
                <div className="text-[10px] text-text-dim">点赞</div>
              </div>
            )}
            {result.metrics.comments !== undefined && (
              <div className="text-center">
                <div className="text-lg font-bold text-secondary">{formatMetric(result.metrics.comments)}</div>
                <div className="text-[10px] text-text-dim">评论</div>
              </div>
            )}
            {result.metrics.shares !== undefined && (
              <div className="text-center">
                <div className="text-lg font-bold text-yellow-400">{formatMetric(result.metrics.shares)}</div>
                <div className="text-[10px] text-text-dim">分享</div>
              </div>
            )}
          </div>
        )}

        {/* Tags */}
        {result.tags && result.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {result.tags.map((tag, i) => (
              <span
                key={i}
                className="px-2 py-0.5 text-[10px] rounded-full bg-gray-700/50 text-gray-300 border border-gray-600/50"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="prose prose-invert prose-sm max-w-none">
          <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
            {result.content || result.snippet}
          </div>
        </div>
      </div>
    </div>
  );
};

// Filter controls component
const FilterBar: React.FC<{
  sourceFilter: string | null;
  sentimentFilter: string | null;
  onSourceChange: (source: string | null) => void;
  onSentimentChange: (sentiment: string | null) => void;
  facets?: { sources?: Record<string, number>; sentiments?: Record<string, number> };
}> = ({ sourceFilter, sentimentFilter, onSourceChange, onSentimentChange, facets }) => {
  const sources: { value: SearchSource | null; label: string }[] = [
    { value: null, label: '全部来源' },
    { value: 'weixin', label: 'WeChat' },
    { value: 'zhihu', label: '知乎' },
    { value: 'weibo', label: '微博' },
    { value: 'xhs', label: '小红书' },
    { value: 'douyin', label: '抖音' },
    { value: 'web', label: 'Web' },
  ];

  const sentiments: { value: Sentiment | null; label: string; icon: string }[] = [
    { value: null, label: '全部情感', icon: 'select_all' },
    { value: 'positive', label: '正面', icon: 'sentiment_satisfied' },
    { value: 'neutral', label: '中性', icon: 'sentiment_neutral' },
    { value: 'negative', label: '负面', icon: 'sentiment_dissatisfied' },
  ];

  return (
    <div className="flex gap-2 flex-wrap">
      <select
        value={sourceFilter || ''}
        onChange={(e) => onSourceChange(e.target.value || null)}
        className="px-2 py-1 text-xs bg-surface-dark border border-border-dark rounded text-white focus:outline-none focus:border-primary"
      >
        {sources.map((s) => (
          <option key={s.value || 'all'} value={s.value || ''}>
            {s.label} {facets?.sources?.[s.value || ''] ? `(${facets.sources[s.value || '']})` : ''}
          </option>
        ))}
      </select>

      <select
        value={sentimentFilter || ''}
        onChange={(e) => onSentimentChange(e.target.value || null)}
        className="px-2 py-1 text-xs bg-surface-dark border border-border-dark rounded text-white focus:outline-none focus:border-primary"
      >
        {sentiments.map((s) => (
          <option key={s.value || 'all'} value={s.value || ''}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  results,
  totalCount,
  isLoading,
  selectedId,
  onSelectResult,
  onClose,
}) => {
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [sentimentFilter, setSentimentFilter] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  // Filter results client-side
  const filteredResults = results.filter((r) => {
    if (sourceFilter && r.source !== sourceFilter) return false;
    if (sentimentFilter && r.sentiment !== sentimentFilter) return false;
    return true;
  });

  const selectedResult = results.find((r) => r.id === selectedId);

  const handleSelectResult = (id: string) => {
    onSelectResult(id);
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
  };

  return (
    <aside className="w-96 bg-surface-darker border-l border-border-dark flex flex-col shrink-0 h-full animate-in slide-in-from-right duration-300">
      {/* Show detail view or list view */}
      {showDetail && selectedResult ? (
        <ResultDetail result={selectedResult} onClose={handleBackToList} />
      ) : (
        <>
          {/* Header */}
          <div className="p-4 border-b border-border-dark">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold uppercase tracking-widest text-text-dim flex items-center gap-2 font-display">
                <span className="material-symbols-outlined text-secondary text-sm">search_insights</span>
                搜索结果
              </h2>
              <button
                onClick={onClose}
                className="text-text-dim hover:text-white transition-colors"
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">
                共 <span className="text-primary font-bold">{totalCount}</span> 条结果
                {filteredResults.length !== totalCount && (
                  <span className="text-gray-500"> (已筛选 {filteredResults.length} 条)</span>
                )}
              </span>
            </div>

            {/* Filters */}
            <div className="mt-3">
              <FilterBar
                sourceFilter={sourceFilter}
                sentimentFilter={sentimentFilter}
                onSourceChange={setSourceFilter}
                onSentimentChange={setSentimentFilter}
              />
            </div>
          </div>

          {/* Results list */}
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-3">
            {isLoading ? (
              // Loading skeleton
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-3 bg-surface-dark border border-border-dark rounded-lg animate-pulse">
                    <div className="h-3 bg-gray-700 rounded w-16 mb-2"></div>
                    <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-700 rounded w-full"></div>
                    <div className="h-3 bg-gray-700 rounded w-2/3 mt-1"></div>
                  </div>
                ))}
              </div>
            ) : filteredResults.length === 0 ? (
              // Empty state
              <div className="flex flex-col items-center justify-center py-12 text-text-dim">
                <span className="material-symbols-outlined text-4xl mb-2 opacity-50">search_off</span>
                <p className="text-sm">暂无结果</p>
                {(sourceFilter || sentimentFilter) && (
                  <button
                    onClick={() => {
                      setSourceFilter(null);
                      setSentimentFilter(null);
                    }}
                    className="text-xs text-primary mt-2 hover:underline"
                  >
                    清除筛选条件
                  </button>
                )}
              </div>
            ) : (
              // Results list
              filteredResults.map((result) => (
                <ResultCard
                  key={result.id}
                  result={result}
                  isSelected={selectedId === result.id}
                  onClick={() => handleSelectResult(result.id)}
                />
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-border-dark bg-surface-darker">
            <div className="flex items-center justify-between text-xs text-text-dim">
              <span>数据来源: GCR 多平台</span>
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-secondary animate-pulse"></span>
                实时更新
              </span>
            </div>
          </div>
        </>
      )}
    </aside>
  );
};

// Helper function
function formatMetric(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}
