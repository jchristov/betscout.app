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
        message: `Method "${req.method}" not found. Supported MCP methods: initialize, ping, tools/list, tools/call.`,
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
