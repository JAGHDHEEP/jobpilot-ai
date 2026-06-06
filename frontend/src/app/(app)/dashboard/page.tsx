"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Recommendation, Analytics } from "@/lib/types";
import { ScoreRing } from "@/components/score-ring";
import { salaryRange } from "@/lib/utils";

export default function DashboardPage() {
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [building, setBuilding] = useState(false);

  async function load() {
    const [r, a] = await Promise.allSettled([
      api<Recommendation[]>("/jobs/recommendations/today"),
      api<Analytics>("/applications/analytics"),
    ]);
    if (r.status === "fulfilled") setRecs(r.value);
    if (a.status === "fulfilled") setAnalytics(a.value);
  }
  useEffect(() => { load(); }, []);

  async function build() {
    setBuilding(true);
    try { await api("/jobs/recommendations/build", { method: "POST" }); await load(); }
    finally { setBuilding(false); }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Today&apos;s top matches</h1>
        <button className="btn-primary" onClick={build} disabled={building}>
          {building ? "Building…" : "Refresh recommendations"}
        </button>
      </div>

      {recs && recs.length > 0 && (() => {
        const strong = recs.filter((r) => (r.match?.overall_score ?? 0) >= 85).length;
        return (
          <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-700 dark:border-brand-700/40 dark:bg-brand-700/10 dark:text-brand-200">
            🎯 <b>{strong}</b> job{strong === 1 ? "" : "s"} above 85% match today · {recs.length} total recommendations
          </div>
        );
      })()}

      {analytics && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Applications" value={analytics.total} />
          <Stat label="Interviews" value={analytics.funnel.interview ?? 0} />
          <Stat label="Success rate" value={`${Math.round(analytics.success_rate * 100)}%`} />
          <Stat label="Interview rate" value={`${Math.round(analytics.interview_rate * 100)}%`} />
        </div>
      )}

      {recs === null ? (
        <div className="grid gap-4">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-24" />)}</div>
      ) : recs.length === 0 ? (
        <div className="card text-center text-slate-500">
          No recommendations yet. Ingest jobs and click “Refresh recommendations”.
        </div>
      ) : (
        <div className="grid gap-4">
          {recs.map((r) => (
            <Link key={r.job.id} href={`/matches?job=${r.job.id}`} className="card flex items-center gap-4 hover:border-brand-500">
              {r.match && <ScoreRing score={r.match.overall_score} />}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-700/20">#{r.rank}</span>
                  <h3 className="truncate font-semibold">{r.job.title}</h3>
                </div>
                <p className="text-sm text-slate-500">{r.job.company} · {r.job.location ?? "—"} · {salaryRange(r.job.salary_min, r.job.salary_max, r.job.currency)}</p>
                {r.match && r.match.missing_skills.length > 0 && (
                  <p className="mt-1 text-xs text-amber-600">Missing: {r.match.missing_skills.slice(0, 4).join(", ")}</p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
