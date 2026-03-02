"use client";

import { useRouter } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
import { Button } from "@/components/ui/button";
import { LogOut, Menu } from "lucide-react";
import { useAuthStore } from "@/lib/store/auth";

interface HeaderProps {
  children?: React.ReactNode;
}

export function Header({ children }: HeaderProps) {
  const router = useRouter();
  const { logout } = useAuthStore();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Toggle menu">
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold md:hidden">Traderrr</h1>
      </div>
      <div className="flex items-center gap-2">
        {children}
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Logout" onClick={handleLogout}>
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
