"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { SignalFilter } from "@traderrr/types";

interface SignalFilterBarProps { onFilter: (filter: SignalFilter) => void; }

export function SignalFilterBar({ onFilter }: SignalFilterBarProps) {
  const [ticker, setTicker] = useState("");
  const [signalType, setSignalType] = useState("");
  const [minConfidence, setMinConfidence] = useState("");

  function handleApply() {
    const filter: SignalFilter = {};
    if (ticker) filter.ticker = ticker.toUpperCase();
    if (signalType) filter.signal_type = signalType;
    if (minConfidence) filter.min_confidence = parseFloat(minConfidence);
    onFilter(filter);
  }

  function handleReset() {
    setTicker("");
    setSignalType("");
    setMinConfidence("");
    onFilter({});
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Ticker</label>
        <Input placeholder="e.g. AAPL" value={ticker} onChange={(e) => setTicker(e.target.value)} className="w-32" />
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Signal Type</label>
        <Select value={signalType} onChange={(e) => setSignalType(e.target.value)}>
          <option value="">All</option>
          <option value="BUY">Buy</option>
          <option value="SELL">Sell</option>
          <option value="HOLD">Hold</option>
        </Select>
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Min Confidence</label>
        <Input type="number" placeholder="0.6" step="0.1" min="0" max="1" value={minConfidence} onChange={(e) => setMinConfidence(e.target.value)} className="w-24" />
      </div>
      <Button onClick={handleApply} size="sm">Apply</Button>
      <Button onClick={handleReset} variant="outline" size="sm">Reset</Button>
    </div>
  );
}
