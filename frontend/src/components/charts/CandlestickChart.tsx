"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SignalResponse } from "@traderrr/types";

interface OHLCVBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface CandlestickChartProps {
  ticker: string;
  ohlcv: OHLCVBar[];
  signals?: SignalResponse[];
}

/**
 * CandlestickChart — TradingView Lightweight Charts
 *
 * Requires `lightweight-charts` package:
 *   pnpm --filter @traderrr/frontend add lightweight-charts
 *
 * Once installed, this component renders OHLCV candlestick data
 * with BUY/SELL signal markers overlaid at the correct timestamps.
 */
export function CandlestickChart({ ticker, ohlcv, signals }: CandlestickChartProps) {
  const latestBar = ohlcv.length > 0 ? ohlcv[ohlcv.length - 1] : null;
  const signalCount = signals?.length ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{ticker} — Candlestick Chart</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex h-72 items-center justify-center rounded-md border border-dashed bg-muted/50">
          <div className="text-center space-y-2">
            <p className="text-lg font-semibold text-muted-foreground">📈 Chart Area</p>
            <p className="text-sm text-muted-foreground">
              {ohlcv.length} bars loaded{signalCount > 0 ? ` · ${signalCount} signals` : ""}
            </p>
            {latestBar && (
              <p className="text-xs text-muted-foreground">
                Latest: O:{latestBar.open.toFixed(2)} H:{latestBar.high.toFixed(2)} L:{latestBar.low.toFixed(2)} C:{latestBar.close.toFixed(2)}
              </p>
            )}
            <p className="text-xs text-muted-foreground italic">
              Install <code>lightweight-charts</code> for interactive candlestick rendering
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export type { OHLCVBar };
