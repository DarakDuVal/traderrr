import type { RiskMetricsResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RiskMetricsCardProps { metrics: RiskMetricsResponse; }

function MetricItem({ label, value, format = "percent" }: { label: string; value: number | null | undefined; format?: "percent" | "decimal" }) {
  const display = value == null ? "—" : format === "percent" ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold">{display}</p>
    </div>
  );
}

export function RiskMetricsCard({ metrics }: RiskMetricsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-5">
          <MetricItem label="VaR (95%)" value={metrics.var_95} />
          <MetricItem label="Sharpe Ratio" value={metrics.sharpe_ratio} format="decimal" />
          <MetricItem label="Sortino Ratio" value={metrics.sortino_ratio} format="decimal" />
          <MetricItem label="Max Drawdown" value={metrics.max_drawdown} />
          <MetricItem label="Volatility" value={metrics.volatility} />
        </div>
      </CardContent>
    </Card>
  );
}
