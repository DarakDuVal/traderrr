"use client";

import { useState } from "react";
import { useSignals } from "@/lib/hooks/useSignals";
import { SignalTable } from "@/components/signals/SignalTable";
import { SignalCard } from "@/components/signals/SignalCard";
import { SignalFilterBar } from "@/components/signals/SignalFilterBar";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { TrendingUp } from "lucide-react";
import type { SignalFilter, SignalResponse } from "@traderrr/types";

export default function SignalsPage() {
  const [filter, setFilter] = useState<SignalFilter>({});
  const [selectedSignal, setSelectedSignal] = useState<SignalResponse | null>(null);
  const { data, isLoading } = useSignals(filter);

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">Signals</h2>
          <p className="text-sm text-muted-foreground">{data?.total ?? 0} signals</p>
        </div>

        <SignalFilterBar onFilter={setFilter} />

        {isLoading ? (
          <LoadingSpinner className="h-64" size="lg" />
        ) : !data?.signals.length ? (
          <EmptyState
            icon={<TrendingUp className="h-12 w-12" />}
            title="No signals found"
            description="Adjust your filters or wait for new signals to be generated."
          />
        ) : (
          <SignalTable signals={data.signals} onSelect={setSelectedSignal} />
        )}

        <Dialog open={!!selectedSignal} onOpenChange={() => setSelectedSignal(null)}>
          <DialogContent onClose={() => setSelectedSignal(null)}>
            {selectedSignal && <SignalCard signal={selectedSignal} />}
          </DialogContent>
        </Dialog>
      </div>
    </ErrorBoundary>
  );
}
