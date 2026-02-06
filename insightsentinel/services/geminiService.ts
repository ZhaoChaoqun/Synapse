import { GoogleGenAI, Type } from "@google/genai";
import { LogEntry, LogLevel } from "../types";

const generateId = () => Math.random().toString(36).substr(2, 9);
const getCurrentTime = () => {
  const now = new Date();
  return now.toTimeString().split(' ')[0]; // HH:MM:SS
};

export class GeminiService {
  private ai: GoogleGenAI;
  private hasKey: boolean;

  constructor() {
    const key = process.env.API_KEY;
    this.hasKey = !!key;
    if (this.hasKey) {
      this.ai = new GoogleGenAI({ apiKey: key });
    } else {
      console.warn("No API_KEY found. Using mock mode.");
      // Dummy initialization to satisfy TS, though we guard usage with hasKey
      this.ai = new GoogleGenAI({ apiKey: 'dummy' });
    }
  }

  async generateReasoningLogs(prompt: string): Promise<LogEntry[]> {
    if (!this.hasKey) {
      return this.generateMockLogs(prompt);
    }

    try {
      const response = await this.ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: `You are InsightSentinel, an autonomous market monitor system.
        The user has initiated a task: "${prompt}".
        
        Generate 4 to 6 realistic, technical system logs that simulate the execution of this task.
        Use a mix of log levels: INFO, DEBUG, WARN, EXEC, NET, ALERT.
        Include some technical jargon (JSON parsing, API endpoints, node handshakes, sentiment analysis, tensor operations).
        
        Return pure JSON array matching this schema:
        {
          "logs": [
            { "level": "INFO", "message": "Log message here", "details": "optional technical detail" }
          ]
        }
        `,
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              logs: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    level: { type: Type.STRING, enum: Object.values(LogLevel) },
                    message: { type: Type.STRING },
                    details: { type: Type.STRING }
                  },
                  required: ["level", "message"]
                }
              }
            }
          }
        }
      });

      const data = JSON.parse(response.text || '{"logs": []}');
      
      return data.logs.map((log: any) => ({
        id: generateId(),
        timestamp: getCurrentTime(),
        level: log.level as LogLevel,
        message: log.message,
        details: log.details
      }));

    } catch (error) {
      console.error("Gemini API Error:", error);
      return this.generateMockLogs(prompt);
    }
  }

  private generateMockLogs(prompt: string): LogEntry[] {
    const keywords = prompt.split(' ').filter(w => w.length > 3);
    const keyword = keywords[0] || 'Unknown';

    return [
      {
        id: generateId(),
        timestamp: getCurrentTime(),
        level: LogLevel.INFO,
        message: `INIT: Connection to Firehose established for query "${keyword}".`
      },
      {
        id: generateId(),
        timestamp: getCurrentTime(),
        level: LogLevel.DEBUG,
        message: `Parsing data stream from proxy nodes.`,
        details: "Rate limit check: OK (24ms)"
      },
      {
        id: generateId(),
        timestamp: getCurrentTime(),
        level: LogLevel.EXEC,
        message: `Cross-referencing entities against Knowledge Graph.`,
        progress: 65
      },
      {
        id: generateId(),
        timestamp: getCurrentTime(),
        level: LogLevel.NET,
        message: `Updated node weights for [${keyword}] and related clusters.`
      },
      {
        id: generateId(),
        timestamp: getCurrentTime(),
        level: LogLevel.INFO,
        message: `Task complete. 420 new data points indexed.`
      }
    ];
  }
}

export const geminiService = new GeminiService();
