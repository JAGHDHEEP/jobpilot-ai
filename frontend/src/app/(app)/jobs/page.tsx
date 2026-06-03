"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Job, Match } from "@/lib/types";
import { salaryRange } from "@/lib/utils";

interface Page<T> { items: T[]; total: number }

export default function JobsPage() {
  const [q, setQ] = useState("");
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [matching, setMatching] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, Match>>({});

  async function search() {
    setJobs(null);
    const data = await api<Page<Job>>(`/jobs?q=${encodeURIComponent(q)}`);
    setJobs(data.items);
  }
  useEffect(() => { search(); }, []);

  async function ingest() {
    setJobs(null);
    await api("/jobs/ingest", { method: "POST" });
    await search();
  }

  async function match(id: string) {
    setMatching(id);
    try {
      const m = await api<Match>(`/jobs/${id}/match`, { method: "POST" });
      setResult((prev) => ({ ...prev, [id]: m }));
    } finally { setMatching(null); }
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <input className="input" placeholder="Search title, company, skills…" value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} />
        <button className="btn-primary" onClick={search}>Search</button>
        <button className="btn-ghost" onClick={ingest}>Ingest jobs</button>
      </div>

      {jobs === null ? (
        <div className="grid gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-20" />)}</div>
      ) : jobs.length === 0 ? (
        <p className="text-slate-500">No jobs found. Click “Ingest jobs” to pull from connectors.</p>
      ) : (
        <div className="grid gap-3">
          {jobs.map((j) => (
            <div key={j.id} className="card">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="font-semibold">{j.title}</h3>
                  <p className="text-sm text-slate-500">{j.company} · {j.location ?? "—"} · {salaryRange(j.salary_min, j.salary_max, j.currency)}</p>
                  <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">{j.description}</p>
                </div>
                <div className="shrink-0 text-right">
                  {result[j.id] ? (
                    <span className="text-2xl font-bold text-brand-600">{result[j.id].overall_score}</span>
                  ) : (
                    <button className="btn-ghost" onClick={() => match(j.id)} disabled={matching === j.id}>
                      {matching === j.id ? "Scoring…" : "Match me"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
