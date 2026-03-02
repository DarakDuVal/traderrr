import type { RiskMetricsResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface KeyMetricsRowProps { metrics: RiskMetricsResponse | null; }

export function KeyMetricsRow({ metrics }: KeyMetricsRowProps) {
  if (!metrics) return null;

  const items = [
    { label: "Sharpe Ratio", value: metrics.sharpe_ratio?.toFixed(3) ?? "—" },
    { label: "VaR (95%)", value: metrics.var_95 != null ? `${(metrics.var_95 * 100).toFixed(2)}%` : "—" },
    { label: "Max Drawdown", value: metrics.max_drawdown != null ? `${(metrics.max_drawdown * 100).toFixed(2)}%` : "—" },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{item.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{item.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
