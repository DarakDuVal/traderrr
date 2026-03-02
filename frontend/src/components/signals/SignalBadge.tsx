import { Badge } from "@/components/ui/badge";

interface SignalBadgeProps { type: string; }

export function SignalBadge({ type }: SignalBadgeProps) {
  const normalized = type.toUpperCase();
  const variant = normalized === "BUY" ? "success" : normalized === "SELL" ? "destructive" : "secondary";
  return <Badge variant={variant}>{normalized}</Badge>;
}
