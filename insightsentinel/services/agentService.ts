/**
 * Agent API Service
 *
 * Connects to the FastAPI backend for Agent execution.
 * Supports SSE streaming for real-time thought chain updates.
 */

import { LogEntry, LogLevel } from '../types';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

// Phase to LogLevel mapping
const PHASE_TO_LEVEL: Record<string, LogLevel> = {
  'idle': LogLevel.DEBUG,
  'planning': LogLevel.INFO,
  'executing': LogLevel.EXEC,
  'searching': LogLevel.NET,
  'scraping': LogLevel.NET,
  'expanding': LogLevel.INFO,
  'critiquing': LogLevel.WARN,
  'synthesizing': LogLevel.EXEC,
  'recovering': LogLevel.WARN,
  'completed': LogLevel.INFO,
  'failed': LogLevel.ALERT,
};

// Types for API responses
export interface ThoughtStep {
  step_id: string;
  phase: string;
  timestamp: string;
  thought: string;
  action?: string;
  observation?: string;
  progress: number;
  tokens_used: number;
}

export interface TaskResult {
  task_id: string;
  total_tokens: number;
  status: string;
}

export interface AgentTask {
  task_id: string;
  command: string;
  status: string;
  thought_chain: ThoughtStep[];
  result_summary?: string;
  intelligence_count: number;
  total_tokens: number;
  duration_ms?: number;
  created_at?: string;
  completed_at?: string;
}

/**
 * Convert backend ThoughtStep to frontend LogEntry
 */
function thoughtToLog(thought: ThoughtStep): LogEntry {
  const level = PHASE_TO_LEVEL[thought.phase] || LogLevel.INFO;

  // Format timestamp
  const timestamp = thought.timestamp
    ? new Date(thought.timestamp).toTimeString().split(' ')[0]
    : new Date().toTimeString().split(' ')[0];

  // Combine thought and observation
  let message = thought.thought;
  if (thought.action) {
    message = `[${thought.action}] ${message}`;
  }

  return {
    id: thought.step_id,
    timestamp,
    level,
    message,
    details: thought.observation,
    progress: thought.progress,
  };
}

/**
 * Agent API Service class
 */
export class AgentService {
  private baseUrl: string;
  private abortController: AbortController | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl + API_VERSION;
  }

  /**
   * Execute a command with SSE streaming
   *
   * @param command The command to execute
   * @param onThought Callback for each thought step
   * @param onComplete Callback when execution completes
   * @param onError Callback for errors
   */
  async executeWithStream(
    command: string,
    onThought: (log: LogEntry) => void,
    onComplete?: (result: TaskResult) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    // Cancel any existing request
    this.abort();
    this.abortController = new AbortController();

    try {
      const response = await fetch(`${this.baseUrl}/agent/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ command }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('event:')) {
            // Extract event type
            const eventType = line.slice(6).trim();
            continue;
          }

          if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);

              // Check event type from data
              if (parsed.step_id) {
                // ThoughtStep event
                const log = thoughtToLog(parsed);
                onThought(log);
              } else if (parsed.task_id && parsed.status === 'completed') {
                // Complete event
                onComplete?.({
                  task_id: parsed.task_id,
                  total_tokens: parsed.total_tokens || 0,
                  status: parsed.status,
                });
              } else if (parsed.error) {
                // Error event
                onError?.(new Error(parsed.error));
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', data);
            }
          }
        }
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        console.log('Request aborted');
        return;
      }
      onError?.(error as Error);
    }
  }

  /**
   * Execute a command synchronously (non-streaming)
   *
   * @param command The command to execute
   * @returns Complete execution result with all thought steps
   */
  async executeSync(command: string): Promise<{
    status: string;
    thought_chain: LogEntry[];
    total_steps: number;
    total_tokens: number;
  }> {
    const response = await fetch(`${this.baseUrl}/agent/execute/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    return {
      status: data.status,
      thought_chain: data.thought_chain.map((t: ThoughtStep) => thoughtToLog(t)),
      total_steps: data.total_steps,
      total_tokens: data.total_tokens,
    };
  }

  /**
   * Get a task by ID
   */
  async getTask(taskId: string): Promise<AgentTask> {
    const response = await fetch(`${this.baseUrl}/agent/tasks/${taskId}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * List all tasks
   */
  async listTasks(limit: number = 20, offset: number = 0, status?: string): Promise<{
    tasks: AgentTask[];
    total: number;
    limit: number;
    offset: number;
  }> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (status) {
      params.append('status', status);
    }

    const response = await fetch(`${this.baseUrl}/agent/tasks?${params}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Delete a task
   */
  async deleteTask(taskId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/agent/tasks/${taskId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  /**
   * Abort any ongoing request
   */
  abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Check if backend is available
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl.replace(API_VERSION, '')}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const agentService = new AgentService();
