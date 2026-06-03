"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MatchWithJob } from "@/lib/types";
import { ScoreRing } from "@/components/score-ring";
import { scoreColor, salaryRange } from "@/lib/utils";

const BARS: { key: keyof MatchWithJob["match"]; label: string }[] = [
  { key: "skill_score", label: "Skills" },
  { key: "project_score", label: "Projects" },
  { key: "experience_score", label: "Experience" },
  { key: "education_score", label: "Education" },
  { key: "keyword_score", label: "Keywords" },
];

export default function MatchesPage() {
  const [items, setItems] = useState<MatchWithJob[] | null>(null);
  const [selected, setSelected] = useState<MatchWithJob | null>(null);

  useEffect(() => {
    api<MatchWithJob[]>("/jobs/matches/top?limit=50")
      .then((d) => { setItems(d); setSelected(d[0] ?? null); })
      .catch(() => setItems([]));
  }, []);

  if (items === null) return <div className="skeleton h-96" />;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
      <div className="space-y-3">
        <h1 className="text-2xl font-bold">Your job matches</h1>
        {items.length === 0 && <p className="text-slate-500">No matches yet — run a match from Search.</p>}
        {items.map((m) => (
          <button key={m.job.id} onClick={() => setSelected(m)}
            className={`card flex w-full items-center gap-3 text-left hover:border-brand-500 ${selected?.job.id === m.job.id ? "border-brand-500" : ""}`}>
            <ScoreRing score={m.match.overall_score} size={52} />
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{m.job.title}</h3>
              <p className="truncate text-sm text-slate-500">{m.job.company}</p>
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="card h-fit animate-fade-in">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold">{selected.job.title}</h2>
              <p className="text-slate-500">{selected.job.company} · {selected.job.location ?? "—"}</p>
              <p className="mt-1 text-sm text-slate-500">{salaryRange(selected.job.salary_min, selected.job.salary_max, selected.job.currency)}</p>
            </div>
            <ScoreRing score={selected.match.overall_score} size={80} />
          </div>

          <div className="mt-6 space-y-3">
            {BARS.map((b) => {
              const v = selected.match[b.key] as number;
              return (
                <div key={b.key}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{b.label}</span><span className={scoreColor(v)}>{v}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-800">
                    <div className="h-2 rounded-full bg-brand-500" style={{ width: `${v}%` }} />
                  </div>
                </div>
              );
            })}
          </div>

          {selected.match.rationale && (
            <div className="mt-6 rounded-lg bg-slate-50 p-4 text-sm dark:bg-slate-800/50">
              <p className="font-medium">Why this score</p>
              <p className="mt-1 text-slate-600 dark:text-slate-400">{selected.match.rationale}</p>
            </div>
          )}

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Gap title="Missing skills" items={selected.match.missing_skills} />
            <Gap title="Missing keywords" items={selected.match.missing_keywords} />
          </div>
        </div>
      )}
    </div>
  );
}

function Gap({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      {items.length === 0 ? <p className="text-sm text-emerald-600">None 🎉</p> : (
        <div className="flex flex-wrap gap-1.5">
          {items.slice(0, 12).map((s) => (
            <span key={s} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}
