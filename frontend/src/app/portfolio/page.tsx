"use client";

import { useState } from "react";
import { usePositions, usePerformance, useAddPosition, useUpdatePosition, useDeletePosition } from "@/lib/hooks/usePortfolio";
import { PositionList } from "@/components/portfolio/PositionList";
import { AddPositionDialog } from "@/components/portfolio/AddPositionDialog";
import { EditPositionDialog } from "@/components/portfolio/EditPositionDialog";
import { AllocationPieChart } from "@/components/charts/AllocationPieChart";
import { PortfolioLineChart } from "@/components/charts/PortfolioLineChart";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Plus, PieChart } from "lucide-react";
import type { PositionResponse } from "@traderrr/types";

export default function PortfolioPage() {
  const { data: positions, isLoading } = usePositions();
  const { data: performance } = usePerformance();
  const addPosition = useAddPosition();
  const updatePosition = useUpdatePosition();
  const deletePosition = useDeletePosition();

  const [addOpen, setAddOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingPosition, setEditingPosition] = useState<PositionResponse | null>(null);

  function handleEdit(position: PositionResponse) {
    setEditingPosition(position);
    setEditOpen(true);
  }

  function handleDelete(position: PositionResponse) {
    if (confirm(`Remove ${position.ticker} position?`)) {
      deletePosition.mutate(position.id);
    }
  }

  if (isLoading) return <LoadingSpinner className="h-64" size="lg" />;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">Portfolio</h2>
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add Position
          </Button>
        </div>

        {!positions?.length ? (
          <EmptyState
            icon={<PieChart className="h-12 w-12" />}
            title="No positions yet"
            description="Add your first position to start tracking your portfolio."
            action={<Button onClick={() => setAddOpen(true)}>Add Position</Button>}
          />
        ) : (
          <>
            <div className="grid gap-6 lg:grid-cols-2">
              <AllocationPieChart positions={positions} />
              <PortfolioLineChart data={performance ?? []} />
            </div>
            <PositionList positions={positions} onEdit={handleEdit} onDelete={handleDelete} />
          </>
        )}

        <AddPositionDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          onSubmit={(ticker, shares) => {
            addPosition.mutate({ ticker, shares }, { onSuccess: () => setAddOpen(false) });
          }}
          loading={addPosition.isPending}
        />

        <EditPositionDialog
          open={editOpen}
          onOpenChange={setEditOpen}
          position={editingPosition}
          onSubmit={(id, shares) => {
            updatePosition.mutate({ id, data: { shares } }, { onSuccess: () => setEditOpen(false) });
          }}
          loading={updatePosition.isPending}
        />
      </div>
    </ErrorBoundary>
  );
}
