import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { LogPanel } from './components/LogPanel';
import { StatsGrid } from './components/StatsGrid';
import { NetworkMap } from './components/NetworkMap';
import { CommandBar } from './components/CommandBar';
import { LogEntry, LogLevel } from './types';
import { geminiService } from './services/geminiService';

const INITIAL_LOGS: LogEntry[] = [
  { id: '1', timestamp: '14:02:45', level: LogLevel.INFO, message: 'INIT: Connection to Weibo Firehose established via Proxy Node #442.' },
  { id: '2', timestamp: '14:02:48', level: LogLevel.DEBUG, message: 'Parsing JSON stream from API endpoint /v2/stream/douyin.' },
  { id: '3', timestamp: '14:02:50', level: LogLevel.WARN, message: 'High velocity detected on keyword "DeepSeek". Threshold exceeded by 15%.' },
  { id: '4', timestamp: '14:03:01', level: LogLevel.EXEC, message: 'Cross-referencing Douyin trends with WeChat Official Accounts...', progress: 65 },
  { id: '5', timestamp: '14:03:12', level: LogLevel.INFO, message: 'Scraping complete. 1,204 new entities identified.' },
  { id: '6', timestamp: '14:03:15', level: LogLevel.NET, message: 'Updating Knowledge Graph nodes: [Moonshot AI], [Kimi Chat].' },
  { id: '7', timestamp: '14:03:22', level: LogLevel.ALERT, message: 'Negative sentiment spike detected in comment threads ID: #88291.' },
];

export default function App() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleExecute = async (command: string) => {
    setIsProcessing(true);
    
    // Add command echo log
    const cmdLog: LogEntry = {
      id: Math.random().toString(),
      timestamp: new Date().toTimeString().split(' ')[0],
      level: LogLevel.EXEC,
      message: `USER CMD: ${command}`,
      progress: 0
    };
    setLogs(prev => [...prev, cmdLog]);

    try {
      const newLogs = await geminiService.generateReasoningLogs(command);
      
      // Stream logs in one by one for effect
      for (let i = 0; i < newLogs.length; i++) {
        await new Promise(r => setTimeout(r, 800)); // Delay between logs
        setLogs(prev => [...prev, newLogs[i]]);
      }
    } catch (e) {
      console.error(e);
      setLogs(prev => [...prev, {
        id: Math.random().toString(),
        timestamp: new Date().toTimeString().split(' ')[0],
        level: LogLevel.ALERT,
        message: 'System Error: Failed to execute reasoning chain.'
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark font-display text-white overflow-hidden h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 flex overflow-hidden">
        <LogPanel logs={logs} />
        
        <div className="flex-1 flex flex-col relative bg-background-dark grid-bg">
          <StatsGrid />
          <NetworkMap />
          <CommandBar onExecute={handleExecute} isProcessing={isProcessing} />
        </div>
      </main>
    </div>
  );
}