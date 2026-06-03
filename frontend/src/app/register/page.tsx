"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/store/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try { await register(form.email, form.password, form.full_name); router.push("/dashboard"); }
    catch (err) { setError(err instanceof Error ? err.message : "Registration failed"); }
    finally { setLoading(false); }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 animate-fade-in">
        <h1 className="text-2xl font-bold">Create your account</h1>
        {error && <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-600 dark:bg-rose-950">{error}</p>}
        <input className="input" placeholder="Full name" value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        <input className="input" type="email" placeholder="Email" value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <input className="input" type="password" placeholder="Password (min 8 chars)"
          minLength={8} value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating…" : "Create account"}
        </button>
        <p className="text-center text-sm text-slate-500">
          Have an account? <Link href="/login" className="text-brand-600">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
