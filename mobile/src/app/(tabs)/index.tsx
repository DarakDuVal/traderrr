import { useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import type {
  PositionResponse,
  PerformanceResponse,
  RiskMetricsResponse,
  SignalResponse,
} from "@traderrr/types";
import { apiClient } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { SignalBadge } from "@/components/ui/Badge";

export default function DashboardScreen() {
  const [positions, setPositions] = useState<PositionResponse[]>([]);
  const [performance, setPerformance] = useState<PerformanceResponse[]>([]);
  const [risk, setRisk] = useState<RiskMetricsResponse | null>(null);
  const [signals, setSignals] = useState<SignalResponse[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [pos, perf, riskData, sigData] = await Promise.all([
        apiClient.getPositions().catch(() => [] as PositionResponse[]),
        apiClient.getPerformance().catch(() => [] as PerformanceResponse[]),
        apiClient.getRiskMetrics().catch(() => null),
        apiClient.getSignals().catch(() => ({ signals: [], total: 0 })),
      ]);
      setPositions(pos);
      setPerformance(perf);
      setRisk(riskData);
      setSignals(sigData.signals);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchData().finally(() => setLoading(false));
  }, [fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  }, [fetchData]);

  const latestPerf = performance.length > 0 ? performance[performance.length - 1] : null;
  const prevPerf = performance.length > 1 ? performance[performance.length - 2] : null;
  const portfolioValue = latestPerf?.portfolio_value ?? 0;
  const dailyPnL = prevPerf ? portfolioValue - prevPerf.portfolio_value : 0;
  const dailyReturn = latestPerf?.daily_return ?? 0;
  const top5 = signals.slice(0, 5);

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
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#3b82f6" />
      }
    >
      {/* Portfolio Summary */}
      <View style={styles.row}>
        <Card style={styles.flex1}>
          <CardHeader>
            <CardTitle>Portfolio Value</CardTitle>
          </CardHeader>
          <CardContent>
            <Text style={styles.bigValue}>${portfolioValue.toLocaleString()}</Text>
          </CardContent>
        </Card>

        <Card style={styles.flex1}>
          <CardHeader>
            <CardTitle>Daily P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <Text style={[styles.bigValue, { color: dailyPnL >= 0 ? "#22c55e" : "#ef4444" }]}>
              {dailyPnL >= 0 ? "+" : ""}
              ${Math.abs(dailyPnL).toLocaleString()}
            </Text>
            <Text style={styles.subtext}>
              {dailyReturn >= 0 ? "+" : ""}
              {(dailyReturn * 100).toFixed(2)}% today
            </Text>
          </CardContent>
        </Card>
      </View>

      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <Text style={styles.bigValue}>{positions.length}</Text>
          <Text style={styles.subtext}>Active positions</Text>
        </CardContent>
      </Card>

      {/* Risk Metric Chips */}
      {risk && (
        <View style={styles.row}>
          <Card style={styles.flex1}>
            <CardHeader><CardTitle>Sharpe</CardTitle></CardHeader>
            <CardContent>
              <Text style={styles.metricValue}>
                {risk.sharpe_ratio?.toFixed(3) ?? "—"}
              </Text>
            </CardContent>
          </Card>
          <Card style={styles.flex1}>
            <CardHeader><CardTitle>VaR (95%)</CardTitle></CardHeader>
            <CardContent>
              <Text style={styles.metricValue}>
                {risk.var_95 != null ? `${(risk.var_95 * 100).toFixed(2)}%` : "—"}
              </Text>
            </CardContent>
          </Card>
          <Card style={styles.flex1}>
            <CardHeader><CardTitle>Max DD</CardTitle></CardHeader>
            <CardContent>
              <Text style={styles.metricValue}>
                {risk.max_drawdown != null ? `${(risk.max_drawdown * 100).toFixed(2)}%` : "—"}
              </Text>
            </CardContent>
          </Card>
        </View>
      )}

      {/* Top 5 Signals */}
      <Card>
        <CardHeader>
          <CardTitle>Latest Signals</CardTitle>
        </CardHeader>
        <CardContent>
          {top5.length === 0 ? (
            <Text style={styles.subtext}>No signals available</Text>
          ) : (
            top5.map((signal) => (
              <View key={signal.id} style={styles.signalRow}>
                <View style={styles.signalLeft}>
                  <SignalBadge type={signal.signal_type} />
                  <View style={{ marginLeft: 10 }}>
                    <Text style={styles.signalTicker}>{signal.ticker}</Text>
                    <Text style={styles.subtext}>
                      {(signal.confidence * 100).toFixed(0)}% confidence
                    </Text>
                  </View>
                </View>
                <Text style={styles.subtext}>
                  {new Date(signal.created_at).toLocaleTimeString()}
                </Text>
              </View>
            ))
          )}
        </CardContent>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  content: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f172a" },
  errorText: { color: "#f87171", fontSize: 15 },
  row: { flexDirection: "row", gap: 10 },
  flex1: { flex: 1 },
  bigValue: { fontSize: 22, fontWeight: "700", color: "#f8fafc" },
  subtext: { fontSize: 12, color: "#94a3b8", marginTop: 2 },
  metricValue: { fontSize: 18, fontWeight: "700", color: "#f8fafc" },
  signalRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#334155",
  },
  signalLeft: { flexDirection: "row", alignItems: "center" },
  signalTicker: { fontSize: 14, fontWeight: "600", color: "#f8fafc" },
});
