import { useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import type { SignalResponse } from "@traderrr/types";
import { apiClient } from "@/lib/api";
import { useSignalStream } from "@/lib/hooks/useSignalStream";
import { SignalBadge } from "@/components/ui/Badge";

type FilterType = "ALL" | "BUY" | "SELL" | "HOLD";

export default function SignalsScreen() {
  const [restSignals, setRestSignals] = useState<SignalResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<FilterType>("ALL");
  const [tickerFilter, setTickerFilter] = useState("");
  const { signals: liveSignals, connectionStatus } = useSignalStream();

  const fetchSignals = useCallback(async () => {
    try {
      const res = await apiClient.getSignals();
      setRestSignals(res.signals);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load signals");
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchSignals().finally(() => setLoading(false));
  }, [fetchSignals]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchSignals();
    setRefreshing(false);
  }, [fetchSignals]);

  // Merge live signals on top of REST signals, dedup by id
  const merged = [...liveSignals, ...restSignals].reduce<SignalResponse[]>((acc, s) => {
    if (!acc.find((x) => x.id === s.id)) acc.push(s);
    return acc;
  }, []);

  const filtered = merged.filter((s) => {
    if (filter !== "ALL" && s.signal_type.toUpperCase() !== filter) return false;
    if (tickerFilter && !s.ticker.toUpperCase().includes(tickerFilter.toUpperCase())) return false;
    return true;
  });

  const renderItem = ({ item }: { item: SignalResponse }) => (
    <View style={styles.signalCard}>
      <View style={styles.signalHeader}>
        <SignalBadge type={item.signal_type} />
        <Text style={styles.ticker}>{item.ticker}</Text>
        <Text style={styles.confidence}>
          {(item.confidence * 100).toFixed(0)}%
        </Text>
      </View>
      <View style={styles.signalDetails}>
        <Text style={styles.detailText}>
          Entry: ${item.entry_price.toFixed(2)} → Target: ${item.target_price.toFixed(2)}
        </Text>
        <Text style={styles.timestamp}>
          {new Date(item.created_at).toLocaleString()}
        </Text>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Connection indicator */}
      <View style={styles.statusBar}>
        <View
          style={[
            styles.statusDot,
            { backgroundColor: connectionStatus === "connected" ? "#22c55e" : "#ef4444" },
          ]}
        />
        <Text style={styles.statusText}>
          {connectionStatus === "connected" ? "Live" : "Offline"}
        </Text>
      </View>

      {/* Filter bar */}
      <View style={styles.filterRow}>
        {(["ALL", "BUY", "SELL", "HOLD"] as FilterType[]).map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterChip, filter === f && styles.filterChipActive]}
            onPress={() => setFilter(f)}
          >
            <Text
              style={[styles.filterText, filter === f && styles.filterTextActive]}
            >
              {f}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#3b82f6" />
        }
        ListEmptyComponent={
          <Text style={styles.emptyText}>No signals match your filter</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f172a" },
  errorText: { color: "#f87171", fontSize: 15 },
  statusBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 8,
    gap: 6,
  },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12, color: "#94a3b8" },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#1e293b",
  },
  filterChipActive: { backgroundColor: "#3b82f6" },
  filterText: { fontSize: 13, fontWeight: "600", color: "#94a3b8" },
  filterTextActive: { color: "#fff" },
  list: { padding: 16, gap: 10 },
  signalCard: {
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 14,
  },
  signalHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  ticker: { fontSize: 16, fontWeight: "700", color: "#f8fafc", flex: 1 },
  confidence: { fontSize: 14, fontWeight: "600", color: "#3b82f6" },
  signalDetails: { marginTop: 8 },
  detailText: { fontSize: 13, color: "#cbd5e1" },
  timestamp: { fontSize: 11, color: "#64748b", marginTop: 4 },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40, fontSize: 14 },
});
