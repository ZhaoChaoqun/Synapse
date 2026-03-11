export enum LogLevel {
  INFO = 'INFO',
  DEBUG = 'DEBUG',
  WARN = 'WARN',
  EXEC = 'EXEC',
  ALERT = 'ALERT',
  NET = 'NET'
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  details?: string;
  progress?: number; // 0-100 for progress bars
  screenshot?: string; // Base64 encoded browser screenshot
}

export interface MetricCard {
  id: string;
  platform: string;
  icon: string;
  iconColor: string;
  trend: number; // percentage
  trendUp: boolean;
  score: number;
  tags: { label: string; count: string }[];
  colorTheme: string; // 'green', 'blue', 'red', 'white'
}

export interface NetworkNode {
  id: string;
  label: string;
  type: 'core' | 'node' | 'kol' | 'cloud';
  x: number; // Percentage 0-100
  y: number; // Percentage 0-100
  status?: 'active' | 'velocity' | 'normal';
  icon?: string;
  color?: string;
  connectionTo?: string[]; // IDs of nodes this connects to
}

// 搜索结果数据结构
export type SearchSource = 'weixin' | 'zhihu' | 'weibo' | 'xhs' | 'douyin' | 'web';
export type Sentiment = 'positive' | 'neutral' | 'negative';

export interface SearchResult {
  id: string;
  title: string;
  url: string;
  source: SearchSource;
  snippet: string;           // 简短预览 (max 200 chars)
  content?: string;          // 完整内容 (懒加载)
  publishedAt?: string;
  author?: string;
  metrics?: {
    views?: number;
    likes?: number;
    comments?: number;
    shares?: number;
  };
  relevanceScore: number;    // 0-100
  sentiment?: Sentiment;
  tags?: string[];
  scrapedAt: string;
}

export interface SearchResultsResponse {
  taskId: string;
  query: string;
  results: SearchResult[];
  totalCount: number;
  facets?: {
    sources: Record<string, number>;
    sentiments: Record<string, number>;
  };
}

// 实体关系图数据结构
export type EntityType = 'company' | 'product' | 'person' | 'concept' | 'topic';

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  mentions: number;        // 在收集数据中被提及的次数
  sentiment?: Sentiment;   // 整体情感倾向
  description?: string;    // 简短描述
}

export interface EntityRelation {
  sourceId: string;
  targetId: string;
  relationType: 'related' | 'owns' | 'competes' | 'partners' | 'mentions';
  strength: number;        // 关系强度 0-1
}

export interface EntityGraph {
  entities: Entity[];
  relations: EntityRelation[];
  centerEntity?: string;   // 中心实体 ID
  generatedAt: string;
}