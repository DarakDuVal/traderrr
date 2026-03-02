"use client";

import { useState } from "react";
import { useRiskMetrics, useCorrelation, useStressTest } from "@/lib/hooks/useRisk";
import { RiskMetricsCard } from "@/components/risk/RiskMetricsCard";
import { CorrelationHeatmap } from "@/components/charts/CorrelationHeatmap";
import { StressTestPanel } from "@/components/risk/StressTestPanel";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import type { StressTestResponse } from "@traderrr/types";

export default function RiskPage() {
  const { data: metrics, isLoading: metricsLoading } = useRiskMetrics();
  const { data: correlation, isLoading: corrLoading } = useCorrelation();
  const stressTest = useStressTest();
  const [stressResult, setStressResult] = useState<StressTestResponse | null>(null);

  if (metricsLoading || corrLoading) return <LoadingSpinner className="h-64" size="lg" />;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <h2 className="text-3xl font-bold tracking-tight">Risk Analysis</h2>

        {metrics && <RiskMetricsCard metrics={metrics} />}

        {correlation && <CorrelationHeatmap data={correlation} />}

        <StressTestPanel
          onRunTest={(scenario, marketChange, volatilityMultiplier) => {
            stressTest.mutate(
              { scenario, market_change: marketChange, volatility_multiplier: volatilityMultiplier },
              { onSuccess: (data) => setStressResult(data) }
            );
          }}
          result={stressResult}
          loading={stressTest.isPending}
        />
      </div>
    </ErrorBoundary>
  );
}
