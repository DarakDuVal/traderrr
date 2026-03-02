"use client";

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import type { PerformanceResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PortfolioLineChartProps { data: PerformanceResponse[]; }

export function PortfolioLineChart({ data }: PortfolioLineChartProps) {
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString(),
    value: d.portfolio_value,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Portfolio Value</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="date" className="text-xs" tick={{ fill: "currentColor" }} />
              <YAxis className="text-xs" tick={{ fill: "currentColor" }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, "Value"]} />
              <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
