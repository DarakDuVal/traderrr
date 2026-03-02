"use client";

import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";
import type { ConnectionStatus as ConnectionStatusType } from "@/lib/hooks/useWebSocket";

interface ConnectionStatusProps {
  status: ConnectionStatusType;
}

const statusConfig = {
  connected: { color: "bg-green-500", label: "Connected" },
  connecting: { color: "bg-yellow-500 animate-pulse", label: "Reconnecting..." },
  disconnected: { color: "bg-red-500", label: "Disconnected" },
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const config = statusConfig[status];

  return (
    <Tooltip content={config.label}>
      <div className="flex items-center gap-2">
        <div className={cn("h-2.5 w-2.5 rounded-full", config.color)} />
        <span className="text-xs text-muted-foreground hidden sm:inline">{config.label}</span>
      </div>
    </Tooltip>
  );
}
