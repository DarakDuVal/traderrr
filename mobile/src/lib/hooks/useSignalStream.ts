import { useState, useCallback } from "react";
import type { SignalResponse } from "@traderrr/types";
import { useWebSocket } from "./useWebSocket";
import type { ConnectionStatus } from "./useWebSocket";

const MAX_SIGNALS = 100;

export function useSignalStream() {
  const [signals, setSignals] = useState<SignalResponse[]>([]);

  const handleMessage = useCallback((data: Record<string, unknown>) => {
    if (data.type === "signal" && data.payload) {
      setSignals((prev) =>
        [data.payload as SignalResponse, ...prev].slice(0, MAX_SIGNALS),
      );
    }
  }, []);

  const { connectionStatus, send, reconnect } = useWebSocket(handleMessage);

  return { signals, connectionStatus: connectionStatus as ConnectionStatus, send, reconnect };
}
