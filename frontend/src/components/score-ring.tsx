import { scoreColor } from "@/lib/utils";

export function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  return (
    <svg width={size} height={size} className="shrink-0 -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={6} fill="none"
        className="stroke-slate-200 dark:stroke-slate-800" />
      <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={6} fill="none"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset}
        className={`${scoreColor(score)} transition-all`} stroke="currentColor" />
      <text x="50%" y="50%" dy="0.35em" textAnchor="middle"
        className={`rotate-90 fill-current text-sm font-bold ${scoreColor(score)}`}
        style={{ transformOrigin: "center" }}>{score}</text>
    </svg>
  );
}
