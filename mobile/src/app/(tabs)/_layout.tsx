import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: "#0f172a" },
        headerTintColor: "#f8fafc",
        tabBarStyle: { backgroundColor: "#0f172a", borderTopColor: "#1e293b" },
        tabBarActiveTintColor: "#3b82f6",
        tabBarInactiveTintColor: "#64748b",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="grid-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="signals"
        options={{
          title: "Signals",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="pulse-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="portfolio"
        options={{
          title: "Portfolio",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="pie-chart-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
