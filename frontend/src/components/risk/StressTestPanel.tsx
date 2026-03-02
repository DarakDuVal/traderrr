"use client";

import { useState } from "react";
import type { StressTestResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface StressTestPanelProps {
  onRunTest: (scenario: string, marketChange: number, volatilityMultiplier: number) => void;
  result: StressTestResponse | null;
  loading?: boolean;
}

export function StressTestPanel({ onRunTest, result, loading }: StressTestPanelProps) {
  const [scenario, setScenario] = useState("Market Crash");
  const [marketChange, setMarketChange] = useState("-20");
  const [volMultiplier, setVolMultiplier] = useState("1.5");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onRunTest(scenario, parseFloat(marketChange), parseFloat(volMultiplier));
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stress Test</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Scenario</label>
            <Input value={scenario} onChange={(e) => setScenario(e.target.value)} className="w-48" />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Market Change (%)</label>
            <Input type="number" step="0.1" value={marketChange} onChange={(e) => setMarketChange(e.target.value)} className="w-32" />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Vol Multiplier</label>
            <Input type="number" step="0.1" min="0.1" value={volMultiplier} onChange={(e) => setVolMultiplier(e.target.value)} className="w-32" />
          </div>
          <Button type="submit" disabled={loading}>{loading ? "Running..." : "Run Test"}</Button>
        </form>

        {result && (
          <div className="space-y-4">
            <div className="rounded-md border p-4">
              <p className="text-sm text-muted-foreground">Scenario: {result.scenario}</p>
              <p className="text-2xl font-bold">
                Portfolio Impact: <span className={result.portfolio_impact < 0 ? "text-red-500" : "text-green-500"}>
                  {(result.portfolio_impact * 100).toFixed(2)}%
                </span>
              </p>
            </div>
            {Object.keys(result.positions_impact).length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Position</TableHead>
                    <TableHead>Impact</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(result.positions_impact).map(([ticker, impact]) => (
                    <TableRow key={ticker}>
                      <TableCell className="font-medium">{ticker}</TableCell>
                      <TableCell className={impact < 0 ? "text-red-500" : "text-green-500"}>
                        {(impact * 100).toFixed(2)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
