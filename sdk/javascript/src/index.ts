export type VerifyRequest = {
  text: string;
  source_prompt?: string;
  domain?: string;
  team_id?: string;
  metadata?: Record<string, unknown>;
};

export type VerifyResponse = {
  request_id: string;
  overall_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  model_used?: string | null;
  latency_ms?: number | null;
  claims: Array<{
    text: string;
    status: string;
    confidence: number;
    hallucination_type: string;
    explanation: string;
    suggested_correction?: string | null;
    supporting_evidence: Array<Record<string, unknown>>;
    source_urls: string[];
  }>;
  corrected_text?: string | null;
  trace: Record<string, unknown>;
};

export class TruthLayerClient {
  constructor(
    private readonly baseUrl: string,
    private readonly options: { apiKey?: string; fetchImpl?: typeof fetch } = {},
  ) {}

  async verify(request: VerifyRequest | string): Promise<VerifyResponse> {
    const fetchImpl = this.options.fetchImpl ?? fetch;
    const payload: VerifyRequest = typeof request === "string" ? { text: request } : request;
    const response = await fetchImpl(`${this.baseUrl.replace(/\/$/, "")}/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.options.apiKey ? { "X-API-Key": this.options.apiKey } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`AI Truth Layer request failed: ${response.status}`);
    }
    return (await response.json()) as VerifyResponse;
  }
}

export const validator = {
  verify(baseUrl: string, request: VerifyRequest | string, apiKey?: string) {
    return new TruthLayerClient(baseUrl, { apiKey }).verify(request);
  },
};

export const truthLayer = {
  verify(baseUrl: string, request: VerifyRequest | string, apiKey?: string) {
    return new TruthLayerClient(baseUrl, { apiKey }).verify(request);
  },
};
