"use client";

import { useState } from "react";
import type { PositionResponse } from "@traderrr/types";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface EditPositionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  position: PositionResponse | null;
  onSubmit: (id: number, shares: number) => void;
  loading?: boolean;
}

export function EditPositionDialog({ open, onOpenChange, position, onSubmit, loading }: EditPositionDialogProps) {
  const [shares, setShares] = useState("");
  const [lastPositionId, setLastPositionId] = useState<number | null>(null);

  // Sync state when a different position is selected (replaces useEffect)
  if (position && position.id !== lastPositionId) {
    setLastPositionId(position.id);
    setShares(position.shares.toString());
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (position && shares) {
      onSubmit(position.id, parseFloat(shares));
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Edit Position — {position?.ticker}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="edit-shares" className="text-sm font-medium">Shares</label>
            <Input id="edit-shares" type="number" step="0.01" min="0.01" value={shares} onChange={(e) => setShares(e.target.value)} required />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>{loading ? "Saving..." : "Save Changes"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
