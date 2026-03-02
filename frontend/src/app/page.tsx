"use client";

import { usePositions, usePerformance } from "@/lib/hooks/usePortfolio";
import { useSignals } from "@/lib/hooks/useSignals";
import { useRiskMetrics } from "@/lib/hooks/useRisk";
import { PortfolioSummaryCard } from "@/components/dashboard/PortfolioSummaryCard";
import { TopSignalsWidget } from "@/components/dashboard/TopSignalsWidget";
import { KeyMetricsRow } from "@/components/dashboard/KeyMetricsRow";
import { PortfolioLineChart } from "@/components/charts/PortfolioLineChart";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

export default function DashboardPage() {
  const positions = usePositions();
  const performance = usePerformance();
  const signals = useSignals();
  const riskMetrics = useRiskMetrics();

  const isLoading = positions.isLoading || performance.isLoading || signals.isLoading;

  if (isLoading) return <LoadingSpinner className="h-64" size="lg" />;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>

        <PortfolioSummaryCard
          positions={positions.data ?? []}
          performance={performance.data ?? []}
        />

        <KeyMetricsRow metrics={riskMetrics.data ?? null} />

        <div className="grid gap-6 lg:grid-cols-2">
          <PortfolioLineChart data={performance.data ?? []} />
          <TopSignalsWidget signals={signals.data?.signals ?? []} />
        </div>
      </div>
    </ErrorBoundary>
  );
}
