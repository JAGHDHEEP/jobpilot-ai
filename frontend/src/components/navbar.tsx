"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Compass } from "lucide-react";
import { useAuth } from "@/store/auth";
import { ThemeToggle } from "./theme-toggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/matches", label: "Job Matches" },
  { href: "/jobs", label: "Search" },
  { href: "/applications", label: "Applications" },
  { href: "/profile", label: "Profile" },
];

export function Navbar() {
  const { user, loadMe, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  useEffect(() => { loadMe(); }, [loadMe]);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Compass className="text-brand-600" size={22} /> JobPilot AI
        </Link>
        <nav className="hidden flex-1 items-center gap-1 md:flex">
          {user && NAV.map((n) => (
            <Link key={n.href} href={n.href}
              className={cn("rounded-md px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800",
                pathname.startsWith(n.href) && "bg-slate-100 font-medium dark:bg-slate-800")}>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <button className="btn-ghost" onClick={async () => { await logout(); router.push("/login"); }}>
              Sign out
            </button>
          ) : (
            <Link href="/login" className="btn-primary">Sign in</Link>
          )}
        </div>
      </div>
    </header>
  );
}
