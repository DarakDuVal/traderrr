import { View, Text, StyleSheet } from "react-native";

interface CardProps {
  children: React.ReactNode;
  style?: object;
}

interface CardHeaderProps {
  children: React.ReactNode;
}

interface CardTitleProps {
  children: React.ReactNode;
  style?: object;
}

interface CardContentProps {
  children: React.ReactNode;
}

export function Card({ children, style }: CardProps) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function CardHeader({ children }: CardHeaderProps) {
  return <View style={styles.header}>{children}</View>;
}

export function CardTitle({ children, style }: CardTitleProps) {
  return <Text style={[styles.title, style]}>{children}</Text>;
}

export function CardContent({ children }: CardContentProps) {
  return <View style={styles.content}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    overflow: "hidden",
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 4,
  },
  title: {
    fontSize: 13,
    fontWeight: "600",
    color: "#94a3b8",
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingTop: 4,
  },
});
