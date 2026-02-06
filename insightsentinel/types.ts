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