import type { SignalResponse } from "@traderrr/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SignalBadge } from "./SignalBadge";

interface SignalCardProps { signal: SignalResponse; }

export function SignalCard({ signal }: SignalCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-semibold">{signal.ticker}</CardTitle>
        <SignalBadge type={signal.signal_type} />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Confidence</p>
            <p className="font-medium">{(signal.confidence * 100).toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-muted-foreground">Regime</p>
            <p className="font-medium">{signal.regime ?? "—"}</p>
          </div>
          {signal.entry_price && (
            <div>
              <p className="text-muted-foreground">Entry</p>
              <p className="font-medium">${signal.entry_price.toFixed(2)}</p>
            </div>
          )}
          {signal.target_price && (
            <div>
              <p className="text-muted-foreground">Target</p>
              <p className="font-medium">${signal.target_price.toFixed(2)}</p>
            </div>
          )}
          {signal.stop_loss && (
            <div>
              <p className="text-muted-foreground">Stop Loss</p>
              <p className="font-medium">${signal.stop_loss.toFixed(2)}</p>
            </div>
          )}
          <div>
            <p className="text-muted-foreground">Date</p>
            <p className="font-medium">{new Date(signal.date).toLocaleDateString()}</p>
          </div>
        </div>
        {signal.reasons && signal.reasons.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-muted-foreground mb-1">Reasons</p>
            <ul className="list-disc list-inside text-sm space-y-0.5">
              {signal.reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
