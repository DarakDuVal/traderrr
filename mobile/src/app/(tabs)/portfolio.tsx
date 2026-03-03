import { useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  TextInput,
  Modal,
  Alert,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { PositionResponse, PositionCreate } from "@traderrr/types";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/Button";

export default function PortfolioScreen() {
  const [positions, setPositions] = useState<PositionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [modalVisible, setModalVisible] = useState(false);
  const [newTicker, setNewTicker] = useState("");
  const [newShares, setNewShares] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchPositions = useCallback(async () => {
    try {
      const pos = await apiClient.getPositions();
      setPositions(pos);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load positions");
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchPositions().finally(() => setLoading(false));
  }, [fetchPositions]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPositions();
    setRefreshing(false);
  }, [fetchPositions]);

  const handleAdd = useCallback(async () => {
    if (!newTicker.trim() || !newShares.trim()) return;

    const shares = Number(newShares);
    if (Number.isNaN(shares) || shares <= 0) {
      Alert.alert("Invalid input", "Shares must be a positive number");
      return;
    }

    setSubmitting(true);
    try {
      const data: PositionCreate = { ticker: newTicker.trim().toUpperCase(), shares };
      const created = await apiClient.addPosition(data);
      setPositions((prev) => [created, ...prev]);
      setModalVisible(false);
      setNewTicker("");
      setNewShares("");
    } catch (err) {
      Alert.alert("Error", err instanceof Error ? err.message : "Failed to add position");
    } finally {
      setSubmitting(false);
    }
  }, [newTicker, newShares]);

  const handleDelete = useCallback(
    (position: PositionResponse) => {
      Alert.alert("Delete Position", `Remove ${position.ticker}?`, [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await apiClient.deletePosition(position.id);
              setPositions((prev) => prev.filter((p) => p.id !== position.id));
            } catch (err) {
              Alert.alert(
                "Error",
                err instanceof Error ? err.message : "Failed to delete position",
              );
            }
          },
        },
      ]);
    },
    [],
  );

  const renderItem = ({ item }: { item: PositionResponse }) => (
    <View style={styles.positionCard}>
      <View style={styles.positionLeft}>
        <Text style={styles.ticker}>{item.ticker}</Text>
        <Text style={styles.shares}>{item.shares} shares</Text>
        <Text style={styles.dateText}>
          Added {new Date(item.created_at).toLocaleDateString()}
        </Text>
      </View>
      <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteBtn}>
        <Ionicons name="trash-outline" size={20} color="#ef4444" />
      </TouchableOpacity>
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
      <FlatList
        data={positions}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#3b82f6" />
        }
        ListEmptyComponent={
          <Text style={styles.emptyText}>No positions yet — tap + to add one</Text>
        }
      />

      {/* Floating Action Button */}
      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>

      {/* Add Position Modal */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Add Position</Text>

            <Text style={styles.label}>Ticker</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. AAPL"
              placeholderTextColor="#64748b"
              value={newTicker}
              onChangeText={setNewTicker}
              autoCapitalize="characters"
            />

            <Text style={styles.label}>Shares</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. 100"
              placeholderTextColor="#64748b"
              value={newShares}
              onChangeText={setNewShares}
              keyboardType="numeric"
            />

            <View style={styles.modalActions}>
              <Button
                title="Cancel"
                variant="secondary"
                onPress={() => setModalVisible(false)}
              />
              <Button
                title={submitting ? "Adding..." : "Add Position"}
                onPress={handleAdd}
                disabled={submitting}
              />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0f172a" },
  errorText: { color: "#f87171", fontSize: 15 },
  list: { padding: 16, gap: 10, paddingBottom: 80 },
  positionCard: {
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  positionLeft: { flex: 1 },
  ticker: { fontSize: 16, fontWeight: "700", color: "#f8fafc" },
  shares: { fontSize: 14, color: "#cbd5e1", marginTop: 2 },
  dateText: { fontSize: 11, color: "#64748b", marginTop: 2 },
  deleteBtn: { padding: 8 },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#3b82f6",
    justifyContent: "center",
    alignItems: "center",
    elevation: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  emptyText: { color: "#64748b", textAlign: "center", marginTop: 40, fontSize: 14 },
  modalOverlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  modalSheet: {
    backgroundColor: "#1e293b",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    paddingBottom: 40,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: "#475569",
    alignSelf: "center",
    marginBottom: 16,
  },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#f8fafc", marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", color: "#cbd5e1", marginBottom: 6, marginTop: 8 },
  input: {
    backgroundColor: "#0f172a",
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: "#f8fafc",
    borderWidth: 1,
    borderColor: "#334155",
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 10,
    marginTop: 20,
  },
});
