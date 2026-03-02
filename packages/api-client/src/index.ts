import type {
  TokenResponse,
  UserResponse,
  SignalFilter,
  SignalListResponse,
  PositionCreate,
  PositionUpdate,
  PositionResponse,
  PerformanceResponse,
  RiskMetricsResponse,
  CorrelationResponse,
  StressTestRequest,
  StressTestResponse,
} from "@traderrr/types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  private baseUrl: string;
  private getToken: () => string | null;

  constructor(baseUrl: string, getToken: () => string | null = () => null) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.getToken = getToken;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}/api/v1${path}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const body = await response.text();
      let message: string;
      try {
        const json = JSON.parse(body);
        message = json.detail || json.message || response.statusText;
      } catch {
        message = body || response.statusText;
      }
      throw new ApiError(response.status, message);
    }

    if (response.status === 204 || response.headers.get("content-length") === "0") {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  // ── Auth ──

  async login(username: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  async refresh(): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/refresh", {
      method: "POST",
    });
  }

  async logout(): Promise<void> {
    return this.request<void>("/auth/logout", {
      method: "POST",
    });
  }

  async me(): Promise<UserResponse> {
    return this.request<UserResponse>("/auth/me");
  }

  // ── Signals ──

  async getSignals(filter?: SignalFilter): Promise<SignalListResponse> {
    const params = new URLSearchParams();
    if (filter) {
      if (filter.ticker) params.set("ticker", filter.ticker);
      if (filter.signal_type) params.set("signal_type", filter.signal_type);
      if (filter.min_confidence != null) params.set("min_confidence", String(filter.min_confidence));
      if (filter.date_from) params.set("date_from", filter.date_from);
      if (filter.date_to) params.set("date_to", filter.date_to);
    }
    const qs = params.toString();
    return this.request<SignalListResponse>(`/signals/${qs ? `?${qs}` : ""}`);
  }

  async getSignalsByTicker(ticker: string): Promise<SignalListResponse> {
    return this.request<SignalListResponse>(`/signals/${encodeURIComponent(ticker)}`);
  }

  // ── Portfolio ──

  async getPositions(): Promise<PositionResponse[]> {
    return this.request<PositionResponse[]>("/portfolio/");
  }

  async addPosition(data: PositionCreate): Promise<PositionResponse> {
    return this.request<PositionResponse>("/portfolio/positions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updatePosition(id: number, data: PositionUpdate): Promise<PositionResponse> {
    return this.request<PositionResponse>(`/portfolio/positions/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deletePosition(id: number): Promise<void> {
    return this.request<void>(`/portfolio/positions/${id}`, {
      method: "DELETE",
    });
  }

  async getPerformance(): Promise<PerformanceResponse[]> {
    return this.request<PerformanceResponse[]>("/portfolio/performance");
  }

  // ── Risk ──

  async getRiskMetrics(): Promise<RiskMetricsResponse> {
    return this.request<RiskMetricsResponse>("/risk/metrics");
  }

  async getCorrelation(): Promise<CorrelationResponse> {
    return this.request<CorrelationResponse>("/risk/correlation");
  }

  async stressTest(data: StressTestRequest): Promise<StressTestResponse> {
    return this.request<StressTestResponse>("/risk/stress-test", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}
