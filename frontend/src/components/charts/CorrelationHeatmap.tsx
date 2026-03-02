"use client";

import type { CorrelationResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CorrelationHeatmapProps { data: CorrelationResponse; }

function getColor(value: number): string {
  if (value >= 0.7) return "#ef4444";
  if (value >= 0.4) return "#f97316";
  if (value >= 0.1) return "#facc15";
  if (value >= -0.1) return "#a3a3a3";
  if (value >= -0.4) return "#22d3ee";
  if (value >= -0.7) return "#3b82f6";
  return "#1d4ed8";
}

export function CorrelationHeatmap({ data }: CorrelationHeatmapProps) {
  const { tickers, matrix } = data;
  const size = tickers.length;
  const cellSize = 60;
  const labelWidth = 60;

  if (size === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Correlation Matrix</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <svg
            width={labelWidth + size * cellSize}
            height={labelWidth + size * cellSize}
            className="text-xs"
          >
            {/* Column labels */}
            {tickers.map((ticker, i) => (
              <text
                key={`col-${i}`}
                x={labelWidth + i * cellSize + cellSize / 2}
                y={labelWidth - 8}
                textAnchor="middle"
                fill="currentColor"
                fontSize={11}
              >
                {ticker}
              </text>
            ))}
            {/* Rows */}
            {matrix.map((row, i) => (
              <g key={`row-${i}`}>
                <text
                  x={labelWidth - 8}
                  y={labelWidth + i * cellSize + cellSize / 2 + 4}
                  textAnchor="end"
                  fill="currentColor"
                  fontSize={11}
                >
                  {tickers[i]}
                </text>
                {row.map((value, j) => (
                  <g key={`cell-${i}-${j}`}>
                    <rect
                      x={labelWidth + j * cellSize}
                      y={labelWidth + i * cellSize}
                      width={cellSize - 2}
                      height={cellSize - 2}
                      fill={getColor(value)}
                      rx={4}
                      opacity={0.85}
                    />
                    <text
                      x={labelWidth + j * cellSize + cellSize / 2 - 1}
                      y={labelWidth + i * cellSize + cellSize / 2 + 4}
                      textAnchor="middle"
                      fill="white"
                      fontSize={11}
                      fontWeight="bold"
                    >
                      {value.toFixed(2)}
                    </text>
                  </g>
                ))}
              </g>
            ))}
          </svg>
        </div>
      </CardContent>
    </Card>
  );
}
