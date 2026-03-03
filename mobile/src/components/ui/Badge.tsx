import { View, Text, StyleSheet } from "react-native";

type BadgeVariant = "success" | "destructive" | "secondary";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
}

const bgColors: Record<BadgeVariant, string> = {
  success: "rgba(34,197,94,0.15)",
  destructive: "rgba(239,68,68,0.15)",
  secondary: "rgba(148,163,184,0.15)",
};

const textColors: Record<BadgeVariant, string> = {
  success: "#22c55e",
  destructive: "#ef4444",
  secondary: "#94a3b8",
};

export function Badge({ label, variant = "secondary" }: BadgeProps) {
  return (
    <View style={[styles.badge, { backgroundColor: bgColors[variant] }]}>
      <Text style={[styles.label, { color: textColors[variant] }]}>{label}</Text>
    </View>
  );
}

export function SignalBadge({ type }: { type: string }) {
  const normalized = type.toUpperCase();
  const variant: BadgeVariant =
    normalized === "BUY" ? "success" : normalized === "SELL" ? "destructive" : "secondary";
  return <Badge label={normalized} variant={variant} />;
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: 12,
    fontWeight: "700",
  },
});
