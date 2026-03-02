// ── Auth ──

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string | null;
}

// ── Signals ──

export interface SignalFilter {
  ticker?: string;
  signal_type?: string;
  min_confidence?: number;
  date_from?: string;
  date_to?: string;
}

export interface SignalResponse {
  id: number;
  ticker: string;
  date: string;
  signal_type: string;
  signal_value: number;
  confidence: number;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  regime: string;
  reasons: string[];
  created_at: string;
}

export interface SignalListResponse {
  signals: SignalResponse[];
  total: number;
}

// ── Portfolio ──

export interface PositionCreate {
  ticker: string;
  shares: number;
}

export interface PositionUpdate {
  shares?: number;
}

export interface PositionResponse {
  id: number;
  ticker: string;
  shares: number;
  created_at: string;
  updated_at: string;
}

export interface PerformanceResponse {
  date: string;
  portfolio_value: number;
  daily_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

// ── Risk ──

export interface RiskMetricsResponse {
  var_95?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  volatility?: number;
  sortino_ratio?: number;
}

export interface CorrelationResponse {
  tickers: string[];
  matrix: number[][];
}

export interface StressTestRequest {
  scenario: string;
  market_change: number;
  volatility_multiplier: number;
}

export interface StressTestResponse {
  scenario: string;
  portfolio_impact: number;
  positions_impact: Record<string, number>;
}

// ── WebSocket ──

export interface WebSocketMessage {
  type: "signal" | "price" | "ping" | "pong";
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface SignalEvent {
  type: "signal";
  payload: SignalResponse;
  timestamp: string;
}

export interface PriceEvent {
  type: "price";
  payload: { ticker: string; price: number; change: number; changePercent: number };
  timestamp: string;
}
