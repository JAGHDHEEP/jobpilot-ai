"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Job, Match } from "@/lib/types";
import { salaryRange, scoreColor } from "@/lib/utils";

interface Page<T> { items: T[]; total: number }

export default function JobsPage() {
  const [q, setQ] = useState("");
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [matches, setMatches] = useState<Record<string, Match>>({});
  const [applied, setApplied] = useState<Record<string, boolean>>({});
  const [note, setNote] = useState("");

  async function search() {
    setJobs(null);
    const data = await api<Page<Job>>(`/jobs?q=${encodeURIComponent(q)}&size=50`);
    setJobs(data.items);
  }
  useEffect(() => { search(); }, []);

  async function ingest() {
    setIngesting(true); setNote("");
    try {
      const r = await api<{ message: string }>("/jobs/ingest", { method: "POST" });
      setNote(r.message);
      await search();
    } catch (e) { setNote(e instanceof Error ? e.message : "Ingest failed"); }
    finally { setIngesting(false); }
  }

  async function match(id: string) {
    setBusy(id);
    try {
      const m = await api<Match>(`/jobs/${id}/match`, { method: "POST" });
      setMatches((p) => ({ ...p, [id]: m }));
    } finally { setBusy(null); }
  }

  async function apply(job: Job) {
    setBusy(job.id);
    try {
      const r = await api<{ apply_url?: string }>(`/jobs/${job.id}/apply`, { method: "POST" });
      setApplied((p) => ({ ...p, [job.id]: true }));
      if (r.apply_url) window.open(r.apply_url, "_blank", "noopener");
    } finally { setBusy(null); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="mb-1 text-2xl font-bold">Find jobs</h1>
        <p className="text-sm text-slate-500">
          “Ingest jobs” pulls live listings from Remotive & Arbeitnow, searched by your
          preferred titles. Then match & apply — your resume is never sent to third parties.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <input className="input max-w-md" placeholder="Search title, company, skill…" value={q}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} />
        <button className="btn-ghost" onClick={search}>Search</button>
        <button className="btn-primary" onClick={ingest} disabled={ingesting}>
          {ingesting ? "Fetching live jobs…" : "Ingest jobs"}
        </button>
      </div>
      {note && <p className="text-sm text-brand-600">{note}</p>}

      {jobs === null ? (
        <div className="grid gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-28" />)}</div>
      ) : jobs.length === 0 ? (
        <p className="text-slate-500">No jobs yet. Click <b>Ingest jobs</b> to pull live listings.</p>
      ) : (
        <div className="grid gap-3">
          {jobs.map((j) => {
            const m = matches[j.id];
            return (
              <div key={j.id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{j.title}</h3>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-500 dark:bg-slate-800">{j.source}</span>
                    </div>
                    <p className="text-sm text-slate-500">
                      {j.company} · {j.location ?? "—"} · {salaryRange(j.salary_min, j.salary_max, j.currency)}
                    </p>
                    <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">{j.description}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    {m ? (
                      <span className={`text-2xl font-bold ${scoreColor(m.overall_score)}`}>{m.overall_score}%</span>
                    ) : (
                      <button className="btn-ghost" onClick={() => match(j.id)} disabled={busy === j.id}>
                        {busy === j.id ? "…" : "Match me"}
                      </button>
                    )}
                    <button className="btn-primary" onClick={() => apply(j)} disabled={busy === j.id}>
                      {applied[j.id] ? "Applied ✓" : "Apply"}
                    </button>
                  </div>
                </div>

                {m && (
                  <div className="mt-3 border-t border-slate-100 pt-3 text-sm dark:border-slate-800">
                    <div className="flex flex-wrap gap-x-6 gap-y-1 text-slate-600 dark:text-slate-400">
                      <span>Skills <b className={scoreColor(m.skill_score)}>{m.skill_score}%</b></span>
                      <span>Experience <b className={scoreColor(m.experience_score)}>{m.experience_score}%</b></span>
                      <span>Keywords <b className={scoreColor(m.keyword_score)}>{m.keyword_score}%</b></span>
                    </div>
                    {m.missing_skills.length > 0 && (
                      <p className="mt-2 text-xs text-amber-600">
                        Missing: {m.missing_skills.slice(0, 6).join(", ")}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
