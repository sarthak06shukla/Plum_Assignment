"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  FilePlus2,
  Gauge,
  Inbox,
  LogOut,
  Menu,
  ShieldCheck,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { label: "Dashboard", href: "/", icon: Gauge },
  { label: "Submit Claim", href: "/submit", icon: FilePlus2 },
  { label: "Manual Review", href: "/manual-review", icon: Inbox, adminOnly: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, loading, email, role, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Login page renders without shell
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // Redirect unauthenticated users to login
  if (!loading && !isAuthenticated) {
    router.replace("/login");
    return null;
  }

  // Show nothing while checking auth state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-emerald-600" />
      </div>
    );
  }

  const isAdmin = role?.toUpperCase() === "ADMIN";
  const visibleNav = navItems.filter((item) => !item.adminOnly || isAdmin);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const sidebar = (
    <>
      <div className="flex h-14 items-center gap-2 border-b px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-700 text-white">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-none">Plum OPD</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Claims Operations
          </p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {visibleNav.map((item) => (
          <Link
            href={item.href}
            key={item.href}
            onClick={() => setMobileOpen(false)}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100",
              pathname === item.href && "bg-zinc-100 font-medium",
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="border-t p-3">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-zinc-100">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r bg-white lg:flex">
        {sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="fixed inset-0 bg-black/30"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative z-50 flex h-full w-64 flex-col bg-white">
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4 rounded-md p-1 hover:bg-zinc-100"
            >
              <X className="h-4 w-4" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              className="rounded-md p-1.5 hover:bg-zinc-100 lg:hidden"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="text-sm font-semibold">OPD Claim Adjudication</p>
              <p className="text-xs text-muted-foreground">
                Audit-ready policy decisions
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {role && (
              <span className="hidden rounded-md border px-2 py-1 capitalize sm:inline">
                {role.toLowerCase()}
              </span>
            )}
            {email && (
              <span className="rounded-md border bg-zinc-50 px-2 py-1">
                {email}
              </span>
            )}
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-5 lg:px-6">{children}</main>
      </div>
    </div>
  );
}
