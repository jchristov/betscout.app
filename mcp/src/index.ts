#!/usr/bin/env node
/**
 * BetScout MCP Server (`@betscout/mcp-server`).
 * Supports stdio JSON-RPC 2.0 transport (`initialize`, `ping`, `tools/list`, `tools/call`)
 * and exports `BetScoutMcpServer` for programmatic or HTTP embedding.
 */

import readline from 'node:readline';
import { BetScoutMcpBackendClient, type McpBackendOptions } from './client.js';
import {
  MCP_TOOLS_CATALOG,
  type McpToolCallResult,
  type McpToolDefinition,
  executeBetScoutMcpTool,
} from './tools/index.js';

export { BetScoutMcpBackendClient, type McpBackendOptions } from './client.js';
export { BetScoutMcpError, formatMcpToolError } from './errors.js';
export { decodeCursor, encodeCursor, paginateItems, type PaginatedResult } from './pagination.js';
export {
  MCP_TOOLS_CATALOG,
  executeBetScoutMcpTool,
  type McpToolCallResult,
  type McpToolDefinition,
} from './tools/index.js';

export const MCP_PROTOCOL_VERSION = '2024-11-05';
export const MCP_SERVER_INFO = {
  name: '@betscout/mcp-server',
  version: '1.1.0',
};

export const MCP_PROMPTS_CATALOG = [
  {
    name: 'daily-bankers',
    description:
      "Retrieve today's highest-conviction BetScout picks across all sports and present a ranked summary table with model probabilities, bookmaker odds, and exact-score/set-score targets.",
    arguments: [
      {
        name: 'sport',
        description:
          "Optional sport category filter ('all', 'soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
        required: false,
      },
      {
        name: 'min_win_prob',
        description: "Minimum calibrated win probability threshold (e.g. '0.70' for >=70%). Default: '0.70'.",
        required: false,
      },
    ],
  },
  {
    name: 'parlay-builder',
    description:
      'Build 2-leg and 3-leg Banker Profitability Booster combo tickets with Quarter-Kelly EUR stake allocations for a specified bankroll budget.',
    arguments: [
      {
        name: 'budget_eur',
        description: "Total EUR budget to allocate across combo tickets (e.g. '100'). Default: '100'.",
        required: false,
      },
    ],
  },
  {
    name: 'set-score-audit',
    description:
      'Analyze one or more Tennis matchups for fixed straight-sets (2:0 / 0:2) probability, +1.5 Sets shield, turnaround warnings, and equal-payout set-score dutching.',
    arguments: [
      {
        name: 'matchups',
        description:
          "Comma-separated tennis matchups (e.g. 'Tommy Paul vs Luciano Darderi, Daniil Medvedev vs Cameron Norrie').",
        required: true,
      },
    ],
  },
  {
    name: 'match-deep-dive',
    description:
      'Run a full quantitative + Match Center inspection on a specific Football or Tennis matchup, including H2H history, Last-6 form, missing players, and equal-payout exact-score dutching.',
    arguments: [
      {
        name: 'matchup',
        description: "Matchup formatted as 'Home vs Away' (e.g. 'AS Roma vs Cagliari', 'Genoa vs Juventus').",
        required: true,
      },
      {
        name: 'stake_eur',
        description: "Optional EUR stake for exact-score dutching split (default: '25').",
        required: false,
      },
    ],
  },
] as const;

export const MCP_RESOURCES_CATALOG = [
  {
    uri: 'betscout://slate/today',
    name: "Today's Active High-Conviction Picks Slate",
    description:
      "Live JSON snapshot of BetScout's active multi-sport picks, model win probabilities, fair odds, and mispriced bookmaker edges.",
    mimeType: 'application/json',
  },
  {
    uri: 'betscout://ledger/summary',
    name: 'Verified Out-of-Sample Paper-Betting Ledger Summary',
    description:
      'Audited Win-Loss record, net unit profit (+u), ROI%, Closing Line Value (CLV%), by-sport breakdown, and recent resolved bets.',
    mimeType: 'application/json',
  },
  {
    uri: 'betscout://boosters/today',
    name: 'Recommended 2-Leg & 3-Leg Banker Profit Boosters',
    description:
      'High-probability (>=72%) 2-leg and 3-leg combo tickets with Quarter-Kelly stake allocations for a €100 reference budget.',
    mimeType: 'application/json',
  },
  {
    uri: 'betscout://cache/telemetry',
    name: '2-Tier Gismo L1/L2 Cache Telemetry',
    description:
      'Real-time hit/miss, negative-cache, and SDK cache metrics for the Sportradar/Tipico Gismo data layer.',
    mimeType: 'application/json',
  },
] as const;

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  id?: string | number | null;
  method: string;
  params?: Record<string, any>;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: string | number | null;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

export class BetScoutMcpServer {
  public readonly client: BetScoutMcpBackendClient;

  constructor(options: McpBackendOptions = {}) {
    this.client = new BetScoutMcpBackendClient(options);
  }

  public async handleJsonRpc(
    request: JsonRpcRequest | JsonRpcRequest[],
  ): Promise<JsonRpcResponse | JsonRpcResponse[] | null> {
    if (Array.isArray(request)) {
      const results: JsonRpcResponse[] = [];
      for (const item of request) {
        const res = await this.handleSingleRequest(item);
        if (res !== null) results.push(res);
      }
      return results;
    }
    return await this.handleSingleRequest(request);
  }

  private async handleSingleRequest(req: JsonRpcRequest): Promise<JsonRpcResponse | null> {
    if (!req || typeof req !== 'object' || req.jsonrpc !== '2.0' || !req.method) {
      return {
        jsonrpc: '2.0',
        id: req?.id ?? null,
        error: {
          code: -32600,
          message: 'Invalid JSON-RPC 2.0 request object.',
        },
      };
    }

    // Notifications do not have an `id` and expect no response
    if (req.id === undefined && req.method.startsWith('notifications/')) {
      return null;
    }

    const id = req.id ?? null;
    const params = req.params ?? {};

    if (req.method === 'initialize') {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          protocolVersion: MCP_PROTOCOL_VERSION,
          capabilities: {
            tools: { listChanged: false },
            prompts: { listChanged: false },
            resources: { subscribe: false, listChanged: false },
          },
          serverInfo: MCP_SERVER_INFO,
        },
      };
    }

    if (req.method === 'ping') {
      return {
        jsonrpc: '2.0',
        id,
        result: {},
      };
    }

    if (req.method === 'tools/list') {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          tools: MCP_TOOLS_CATALOG,
        },
      };
    }

    if (req.method === 'prompts/list') {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          prompts: MCP_PROMPTS_CATALOG,
        },
      };
    }

    if (req.method === 'prompts/get') {
      const promptName = String(params.name ?? '');
      const pArgs = params.arguments && typeof params.arguments === 'object' ? params.arguments : {};
      const found = MCP_PROMPTS_CATALOG.find((p) => p.name === promptName);
      if (!found) {
        return {
          jsonrpc: '2.0',
          id,
          error: {
            code: -32602,
            message: `Unknown prompt "${promptName}". Available prompts: ${MCP_PROMPTS_CATALOG.map((p) => p.name).join(', ')}.`,
          },
        };
      }
      return {
        jsonrpc: '2.0',
        id,
        result: {
          description: found.description,
          messages: [
            {
              role: 'user',
              content: {
                type: 'text',
                text: `Execute BetScout workflow "${promptName}" with arguments: ${JSON.stringify(pArgs)}`,
              },
            },
          ],
        },
      };
    }

    if (req.method === 'resources/list') {
      return {
        jsonrpc: '2.0',
        id,
        result: {
          resources: MCP_RESOURCES_CATALOG,
        },
      };
    }

    if (req.method === 'resources/read') {
      const uri = String(params.uri ?? '');
      if (uri === 'betscout://slate/today') {
        const res = await executeBetScoutMcpTool(this.client, 'get_daily_banker_picks', {
          sport: 'all',
          min_win_prob: 0.55,
          limit: 30,
        });
        return {
          jsonrpc: '2.0',
          id,
          result: {
            contents: [{ uri, mimeType: 'application/json', text: res.content[0]?.text ?? '{}' }],
          },
        };
      }
      if (uri === 'betscout://ledger/summary') {
        const res = await executeBetScoutMcpTool(this.client, 'get_paper_ledger_roi', {
          status: 'settled',
          limit: 20,
        });
        return {
          jsonrpc: '2.0',
          id,
          result: {
            contents: [{ uri, mimeType: 'application/json', text: res.content[0]?.text ?? '{}' }],
          },
        };
      }
      if (uri === 'betscout://boosters/today') {
        const res = await executeBetScoutMcpTool(this.client, 'get_banker_profit_boosters', {
          budget_eur: 100,
          max_combos: 6,
        });
        return {
          jsonrpc: '2.0',
          id,
          result: {
            contents: [{ uri, mimeType: 'application/json', text: res.content[0]?.text ?? '{}' }],
          },
        };
      }
      if (uri === 'betscout://cache/telemetry') {
        return {
          jsonrpc: '2.0',
          id,
          result: {
            contents: [
              {
                uri,
                mimeType: 'application/json',
                text: JSON.stringify(this.client.getCacheTelemetry(), null, 2),
              },
            ],
          },
        };
      }
      return {
        jsonrpc: '2.0',
        id,
        error: {
          code: -32602,
          message: `Unknown resource URI "${uri}". Available resources: ${MCP_RESOURCES_CATALOG.map((r) => r.uri).join(', ')}.`,
        },
      };
    }

    if (req.method === 'tools/call') {
      const toolName = String(params.name ?? '');
      const toolArgs =
        params.arguments && typeof params.arguments === 'object' ? params.arguments : {};
      const callResult = await executeBetScoutMcpTool(this.client, toolName, toolArgs);
      return {
        jsonrpc: '2.0',
        id,
        result: callResult,
      };
    }

    return {
      jsonrpc: '2.0',
      id,
      error: {
        code: -32601,
        message: `Method "${req.method}" not found. Supported MCP methods: initialize, ping, tools/list, tools/call, prompts/list, prompts/get, resources/list, resources/read.`,
      },
    };
  }
}

export function startStdioMcpServer(options: McpBackendOptions = {}): BetScoutMcpServer {
  const server = new BetScoutMcpServer(options);
  const rl = readline.createInterface({
    input: process.stdin,
    terminal: false,
  });

  rl.on('line', async (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const parsed = JSON.parse(trimmed);
      const response = await server.handleJsonRpc(parsed);
      if (response !== null) {
        process.stdout.write(`${JSON.stringify(response)}\n`);
      }
    } catch {
      const errResp: JsonRpcResponse = {
        jsonrpc: '2.0',
        id: null,
        error: {
          code: -32700,
          message: 'Parse error: invalid JSON on stdin.',
        },
      };
      process.stdout.write(`${JSON.stringify(errResp)}\n`);
    }
  });

  return server;
}

const isMainModule =
  process.argv[1] &&
  (process.argv[1].endsWith('/mcp/dist/index.js') ||
    process.argv[1].endsWith('\\mcp\\dist\\index.js') ||
    process.argv[1].endsWith('betscout-mcp-server'));

if (isMainModule) {
  startStdioMcpServer();
}
