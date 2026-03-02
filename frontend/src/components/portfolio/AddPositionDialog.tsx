"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface AddPositionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (ticker: string, shares: number) => void;
  loading?: boolean;
}

export function AddPositionDialog({ open, onOpenChange, onSubmit, loading }: AddPositionDialogProps) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (ticker && shares) {
      onSubmit(ticker.toUpperCase(), parseFloat(shares));
      setTicker("");
      setShares("");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Add Position</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="ticker" className="text-sm font-medium">Ticker</label>
            <Input id="ticker" placeholder="e.g. AAPL" value={ticker} onChange={(e) => setTicker(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <label htmlFor="shares" className="text-sm font-medium">Shares</label>
            <Input id="shares" type="number" placeholder="100" step="0.01" min="0.01" value={shares} onChange={(e) => setShares(e.target.value)} required />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>{loading ? "Adding..." : "Add Position"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
