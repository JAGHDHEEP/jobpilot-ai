"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Application, Analytics } from "@/lib/types";

const STATUSES = ["saved", "applied", "interview", "rejected", "offer", "accepted", "withdrawn"];

export default function ApplicationsPage() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  async function load() {
    const [a, an] = await Promise.all([
      api<Application[]>("/applications"),
      api<Analytics>("/applications/analytics"),
    ]);
    setApps(a); setAnalytics(an);
  }
  useEffect(() => { load(); }, []);

  async function setStatus(id: string, status: string) {
    await api(`/applications/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    await load();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Application tracker</h1>
      {analytics && (
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <span key={s} className="rounded-full border border-slate-200 px-3 py-1 text-sm dark:border-slate-700">
              {s}: <b>{analytics.funnel[s] ?? 0}</b>
            </span>
          ))}
        </div>
      )}
      {apps === null ? <div className="skeleton h-64" /> : apps.length === 0 ? (
        <p className="text-slate-500">No applications tracked yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500">
              <tr><th className="p-2">Job</th><th className="p-2">Status</th><th className="p-2">Updated</th></tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id} className="border-t border-slate-200 dark:border-slate-800">
                  <td className="p-2 font-mono text-xs">{a.job_id.slice(0, 8)}</td>
                  <td className="p-2">
                    <select className="input !py-1" value={a.status}
                      onChange={(e) => setStatus(a.id, e.target.value)}>
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="p-2 text-slate-500">{new Date(a.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
