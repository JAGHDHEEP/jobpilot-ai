"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import { Compass, Target, FileText, Sparkles, TrendingUp } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

const FEATURES = [
  { icon: Target, title: "Explainable match scores", desc: "Every job scored /100 across skills, projects, experience, education & keywords — with the why." },
  { icon: FileText, title: "ATS resume optimization", desc: "Truthful, tailored resumes per job. Reorders strengths, weaves in keywords, never invents." },
  { icon: Sparkles, title: "AI cover letters & interview prep", desc: "Grounded in your real profile via RAG. Likely questions, behavioral, technical, company-specific." },
  { icon: TrendingUp, title: "Daily top matches", desc: "Top 50 fresh jobs ranked by match, freshness, salary, company quality & remote." },
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex h-16 max-w-7xl items-center px-4">
        <span className="flex items-center gap-2 text-lg font-semibold">
          <Compass className="text-brand-600" /> JobPilot AI
        </span>
        <div className="ml-auto flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="btn-ghost">Sign in</Link>
          <Link href="/register" className="btn-primary">Get started</Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-4 py-24 text-center">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="text-5xl font-bold tracking-tight sm:text-6xl">
          Your AI career assistant,<br />
          <span className="text-brand-600">not just another job board.</span>
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
          className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-400">
          JobPilot studies your full profile, scores every job with an explainable engine,
          and generates tailored, ATS-ready resumes — so you apply to the right roles, better.
        </motion.p>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
          className="mt-10 flex justify-center gap-4">
          <Link href="/register" className="btn-primary px-6 py-3 text-base">Start free</Link>
          <Link href="/login" className="btn-ghost px-6 py-3 text-base">I have an account</Link>
        </motion.div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-6 px-4 pb-24 sm:grid-cols-2">
        {FEATURES.map((f, i) => (
          <motion.div key={f.title} className="card" initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.05 }}>
            <f.icon className="mb-3 text-brand-600" />
            <h3 className="text-lg font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{f.desc}</p>
          </motion.div>
        ))}
      </section>
    </div>
  );
}
