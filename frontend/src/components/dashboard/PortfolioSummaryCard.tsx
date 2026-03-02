import type { PositionResponse, PerformanceResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, DollarSign, BarChart3 } from "lucide-react";

interface PortfolioSummaryCardProps {
  positions: PositionResponse[];
  performance: PerformanceResponse[];
}

export function PortfolioSummaryCard({ positions, performance }: PortfolioSummaryCardProps) {
  const latestPerf = performance.length > 0 ? performance[performance.length - 1] : null;
  const prevPerf = performance.length > 1 ? performance[performance.length - 2] : null;
  const dailyReturn = latestPerf?.daily_return ?? 0;
  const portfolioValue = latestPerf?.portfolio_value ?? 0;
  const dailyPnL = prevPerf ? portfolioValue - prevPerf.portfolio_value : 0;

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${portfolioValue.toLocaleString()}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Daily P&L</CardTitle>
          {dailyPnL >= 0 ? <TrendingUp className="h-4 w-4 text-green-500" /> : <TrendingDown className="h-4 w-4 text-red-500" />}
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${dailyPnL >= 0 ? "text-green-500" : "text-red-500"}`}>
            {dailyPnL >= 0 ? "+" : ""}{dailyPnL.toLocaleString(undefined, { style: "currency", currency: "USD" })}
          </div>
          <p className="text-xs text-muted-foreground">
            {dailyReturn >= 0 ? "+" : ""}{(dailyReturn * 100).toFixed(2)}% today
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Positions</CardTitle>
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{positions.length}</div>
          <p className="text-xs text-muted-foreground">Active positions</p>
        </CardContent>
      </Card>
    </div>
  );
}
