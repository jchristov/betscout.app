/**
 * Actionable, human-readable error formatting for `@betscout/mcp-server`.
 * Translates raw HTTP, timeout, and validation errors into guidance the model can act on.
 */

export class BetScoutMcpError extends Error {
  public readonly statusCode?: number;
  public readonly remediation: string;

  constructor(message: string, remediation: string, statusCode?: number) {
    super(message);
    this.name = 'BetScoutMcpError';
    this.remediation = remediation;
    this.statusCode = statusCode;
  }
}

export function formatMcpToolError(toolName: string, err: unknown): {
  content: Array<{ type: 'text'; text: string }>;
  isError: true;
} {
  if (err instanceof BetScoutMcpError) {
    return {
      content: [
        {
          type: 'text',
          text: `${err.message} Next step: ${err.remediation}`,
        },
      ],
      isError: true,
    };
  }

  const rawMsg = err instanceof Error ? err.message : String(err);

  if (rawMsg.includes('Invalid pagination cursor')) {
    return {
      content: [{ type: 'text', text: rawMsg }],
      isError: true,
    };
  }

  if (rawMsg.includes('401') || rawMsg.includes('403') || rawMsg.toLowerCase().includes('unauthorized')) {
    return {
      content: [
        {
          type: 'text',
          text: `Authentication or tier authorization failed while calling \`${toolName}\`. Verify that \`BETSCOUT_API_KEY\` is set to an active BetScout Pro/Quant API key, or connect to a local BetScout server instance.`,
        },
      ],
      isError: true,
    };
  }

  if (rawMsg.includes('429') || rawMsg.toLowerCase().includes('rate limit')) {
    return {
      content: [
        {
          type: 'text',
          text: `Rate limit exceeded on \`${toolName}\` (retry in 30 seconds). Prefer narrowing your query with \`sport\` or \`query\` filters rather than scanning all sports simultaneously.`,
        },
      ],
      isError: true,
    };
  }

  if (rawMsg.toLowerCase().includes('abort') || rawMsg.toLowerCase().includes('timeout')) {
    return {
      content: [
        {
          type: 'text',
          text: `Upstream request timed out while executing \`${toolName}\`. Retry once or check \`BETSCOUT_API_URL\` connectivity.`,
        },
      ],
      isError: true,
    };
  }

  return {
    content: [
      {
        type: 'text',
        text: `Error in \`${toolName}\`: ${rawMsg}. Check the required parameters and retry.`,
      },
    ],
    isError: true,
  };
}
