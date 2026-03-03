import { TouchableOpacity, Text, StyleSheet, type ViewStyle, type TextStyle } from "react-native";

type Variant = "primary" | "secondary" | "destructive" | "ghost";
type Size = "default" | "sm" | "icon";

interface ButtonProps {
  title?: string;
  onPress: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  children?: React.ReactNode;
}

const bgColors: Record<Variant, string> = {
  primary: "#3b82f6",
  secondary: "#334155",
  destructive: "#ef4444",
  ghost: "transparent",
};

const textColors: Record<Variant, string> = {
  primary: "#ffffff",
  secondary: "#f8fafc",
  destructive: "#ffffff",
  ghost: "#94a3b8",
};

export function Button({
  title,
  onPress,
  variant = "primary",
  size = "default",
  disabled = false,
  children,
}: ButtonProps) {
  const sizeStyle: ViewStyle =
    size === "sm"
      ? { paddingHorizontal: 12, paddingVertical: 6 }
      : size === "icon"
        ? { width: 36, height: 36, justifyContent: "center", alignItems: "center", padding: 0 }
        : { paddingHorizontal: 16, paddingVertical: 12 };

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.base,
        { backgroundColor: bgColors[variant] },
        sizeStyle,
        disabled && styles.disabled,
      ]}
    >
      {children ?? (
        <Text style={[styles.text, { color: textColors[variant] } as TextStyle]}>
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: 8, alignItems: "center", justifyContent: "center" },
  text: { fontSize: 15, fontWeight: "600" },
  disabled: { opacity: 0.5 },
});
