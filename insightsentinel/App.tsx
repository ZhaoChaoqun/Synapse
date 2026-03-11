import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { LogPanel } from './components/LogPanel';
import { StatsGrid } from './components/StatsGrid';
import { NetworkMap } from './components/NetworkMap';
import { CommandBar } from './components/CommandBar';
import { ResultsPanel } from './components/ResultsPanel';
import { LogEntry, LogLevel, SearchResult, EntityGraph } from './types';
import { agentService } from './services/agentService';
import { geminiService } from './services/geminiService';

const INITIAL_LOGS: LogEntry[] = [
  { id: '1', timestamp: '14:02:45', level: LogLevel.INFO, message: 'INIT: InsightSentinel 系统启动完成' },
  { id: '2', timestamp: '14:02:48', level: LogLevel.DEBUG, message: '正在检查后端服务连接状态...' },
];

// Connection status type
type ConnectionStatus = 'checking' | 'connected' | 'disconnected';

export default function App() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking');
  const [useMockMode, setUseMockMode] = useState(false);

  // Search results state
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResultsPanel, setShowResultsPanel] = useState(false);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  // Entity graph state
  const [entityGraph, setEntityGraph] = useState<EntityGraph | null>(null);
  const [entityGraphLoading, setEntityGraphLoading] = useState(false);

  // Check backend health on mount
  useEffect(() => {
    const checkConnection = async () => {
      setConnectionStatus('checking');
      const isHealthy = await agentService.healthCheck();

      if (isHealthy) {
        setConnectionStatus('connected');
        setUseMockMode(false);
        addLog(LogLevel.INFO, '后端服务连接成功', 'FastAPI backend ready');
      } else {
        setConnectionStatus('disconnected');
        setUseMockMode(true);
        addLog(LogLevel.WARN, '后端服务不可用，切换到演示模式', '使用 Gemini API 模拟推理');
      }
    };

    checkConnection();

    // Periodic health check every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Helper to add a single log
  const addLog = useCallback((level: LogLevel, message: string, details?: string) => {
    const log: LogEntry = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toTimeString().split(' ')[0],
      level,
      message,
      details,
    };
    setLogs(prev => [...prev, log]);
  }, []);

  // Handle command execution
  const handleExecute = async (command: string) => {
    setIsProcessing(true);
    // Reset results for new task
    setSearchResults([]);
    setShowResultsPanel(false);
    setSelectedResultId(null);
    setCurrentTaskId(null);
    setEntityGraph(null);

    // Add command echo log
    addLog(LogLevel.EXEC, `USER CMD: ${command}`);

    if (useMockMode) {
      // Use Gemini mock mode
      await handleMockExecution(command);
    } else {
      // Use real backend with SSE streaming
      await handleRealExecution(command);
    }

    setIsProcessing(false);
  };

  // Real backend execution with SSE streaming
  const handleRealExecution = async (command: string) => {
    try {
      addLog(LogLevel.INFO, '正在连接 Agent 服务...', 'POST /api/v1/agent/execute');

      await agentService.executeWithStream(
        command,
        // onThought - each step from the Agent
        (log: LogEntry) => {
          setLogs(prev => [...prev, log]);
        },
        // onComplete
        async (result) => {
          addLog(
            LogLevel.INFO,
            `任务完成: ${result.task_id}`,
            `消耗 ${result.total_tokens} tokens`
          );

          // Fetch search results after completion
          setCurrentTaskId(result.task_id);
          await fetchTaskResults(result.task_id);
          // Fetch entity graph
          await fetchEntityGraph(result.task_id);
        },
        // onError
        (error) => {
          addLog(LogLevel.ALERT, `执行错误: ${error.message}`);
          // Fall back to mock mode for this request
          handleMockExecution(command);
        }
      );
    } catch (error) {
      console.error('Execution error:', error);
      addLog(LogLevel.ALERT, '连接失败，切换到演示模式');
      setUseMockMode(true);
      await handleMockExecution(command);
    }
  };

  // Fetch task results from backend
  const fetchTaskResults = async (taskId: string) => {
    try {
      setResultsLoading(true);
      const response = await agentService.getTaskResults(taskId);

      if (response.results.length > 0) {
        setSearchResults(response.results);
        setShowResultsPanel(true);
        addLog(
          LogLevel.NET,
          `获取到 ${response.totalCount} 条搜索结果`,
          '点击右侧面板查看详情'
        );
      }
    } catch (error) {
      console.error('Failed to fetch results:', error);
      // Don't show error to user - results might not be available yet
    } finally {
      setResultsLoading(false);
    }
  };

  // Fetch entity graph from backend
  const fetchEntityGraph = async (taskId: string) => {
    try {
      setEntityGraphLoading(true);
      const graph = await agentService.getTaskEntityGraph(taskId);

      if (graph.entities && graph.entities.length > 0) {
        setEntityGraph(graph);
        addLog(
          LogLevel.INFO,
          `实体分析完成: 发现 ${graph.entities.length} 个实体`,
          `${graph.relations?.length || 0} 个关联关系`
        );
      }
    } catch (error) {
      console.error('Failed to fetch entity graph:', error);
    } finally {
      setEntityGraphLoading(false);
    }
  };

  // Mock execution using Gemini
  const handleMockExecution = async (command: string) => {
    try {
      const newLogs = await geminiService.generateReasoningLogs(command);

      // Stream logs one by one for effect
      for (let i = 0; i < newLogs.length; i++) {
        await new Promise(r => setTimeout(r, 600));
        setLogs(prev => [...prev, newLogs[i]]);
      }

      addLog(LogLevel.INFO, '演示任务完成', '这是模拟数据，请启动后端服务获取真实数据');
    } catch (e) {
      console.error(e);
      addLog(LogLevel.ALERT, '系统错误: 无法执行推理链');
    }
  };

  // Handle abort
  const handleAbort = useCallback(() => {
    agentService.abort();
    addLog(LogLevel.WARN, '任务已取消');
    setIsProcessing(false);
    setShowResultsPanel(false);
  }, [addLog]);

  // Handle closing results panel
  const handleCloseResultsPanel = useCallback(() => {
    setShowResultsPanel(false);
    setSelectedResultId(null);
  }, []);

  // Get status indicator color
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-500';
      case 'disconnected': return 'bg-yellow-500';
      case 'checking': return 'bg-blue-500 animate-pulse';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark font-display text-white overflow-hidden h-screen flex flex-col">
      <Header>
        {/* Connection status indicator */}
        <div className="flex items-center gap-2 text-xs">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span className="text-text-dim">
            {connectionStatus === 'connected' && 'Backend Connected'}
            {connectionStatus === 'disconnected' && 'Demo Mode'}
            {connectionStatus === 'checking' && 'Checking...'}
          </span>
        </div>
      </Header>

      <main className="flex-1 flex overflow-hidden">
        <LogPanel logs={logs} />

        <div className={`flex-1 flex flex-col relative bg-background-dark grid-bg transition-all duration-300 ${showResultsPanel ? 'mr-0' : ''}`}>
          <StatsGrid />
          <NetworkMap entityGraph={entityGraph} isLoading={entityGraphLoading} />
          <CommandBar
            onExecute={handleExecute}
            isProcessing={isProcessing}
            onAbort={handleAbort}
          />
        </div>

        {/* Results Panel - slides in from right */}
        {showResultsPanel && (
          <ResultsPanel
            results={searchResults}
            totalCount={searchResults.length}
            isLoading={resultsLoading}
            selectedId={selectedResultId}
            onSelectResult={setSelectedResultId}
            onClose={handleCloseResultsPanel}
          />
        )}
      </main>
    </div>
  );
}
