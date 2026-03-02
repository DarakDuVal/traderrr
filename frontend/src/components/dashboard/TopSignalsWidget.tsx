import type { SignalResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SignalBadge } from "@/components/signals/SignalBadge";

interface TopSignalsWidgetProps { signals: SignalResponse[]; }

export function TopSignalsWidget({ signals }: TopSignalsWidgetProps) {
  const top5 = signals.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest Signals</CardTitle>
      </CardHeader>
      <CardContent>
        {top5.length === 0 ? (
          <p className="text-sm text-muted-foreground">No signals available</p>
        ) : (
          <div className="space-y-3">
            {top5.map((signal) => (
              <div key={signal.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <SignalBadge type={signal.signal_type} />
                  <div>
                    <p className="text-sm font-medium">{signal.ticker}</p>
                    <p className="text-xs text-muted-foreground">
                      {(signal.confidence * 100).toFixed(0)}% confidence
                    </p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">
                  {new Date(signal.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
