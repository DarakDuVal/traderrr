"use client";

import type { SignalResponse } from "@traderrr/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SignalBadge } from "./SignalBadge";

interface SignalTableProps { signals: SignalResponse[]; onSelect?: (signal: SignalResponse) => void; }

export function SignalTable({ signals, onSelect }: SignalTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Confidence</TableHead>
          <TableHead className="hidden sm:table-cell">Entry</TableHead>
          <TableHead className="hidden md:table-cell">Target</TableHead>
          <TableHead className="hidden md:table-cell">Regime</TableHead>
          <TableHead>Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {signals.map((signal) => (
          <TableRow
            key={signal.id}
            className={onSelect ? "cursor-pointer" : ""}
            onClick={() => onSelect?.(signal)}
          >
            <TableCell className="font-medium">{signal.ticker}</TableCell>
            <TableCell><SignalBadge type={signal.signal_type} /></TableCell>
            <TableCell>{(signal.confidence * 100).toFixed(1)}%</TableCell>
            <TableCell className="hidden sm:table-cell">
              {signal.entry_price ? `$${signal.entry_price.toFixed(2)}` : "—"}
            </TableCell>
            <TableCell className="hidden md:table-cell">
              {signal.target_price ? `$${signal.target_price.toFixed(2)}` : "—"}
            </TableCell>
            <TableCell className="hidden md:table-cell">{signal.regime ?? "—"}</TableCell>
            <TableCell>{new Date(signal.date).toLocaleDateString()}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
