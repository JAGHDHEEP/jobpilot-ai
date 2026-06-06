"use client";
import { useEffect, useRef, useState } from "react";
import { api, API_URL } from "@/lib/api";

interface Skill { id: string; name: string; category: string }
interface Profile {
  id: string;
  phone?: string; location?: string; headline?: string; summary?: string;
  current_role?: string; years_experience?: number;
  current_ctc?: string; expected_ctc?: string; notice_period?: string;
  work_mode?: string; preferred_locations: string[]; preferred_titles: string[];
  salary_min?: number; salary_max?: number;
  linkedin_url?: string; github_url?: string; portfolio_url?: string;
  skills: Skill[]; experiences: unknown[]; projects: unknown[]; educations: unknown[];
}

const blank = {
  phone: "", location: "", headline: "", summary: "",
  current_role: "", years_experience: "", current_ctc: "", expected_ctc: "", notice_period: "",
  work_mode: "any", preferred_locations: "", preferred_titles: "",
  salary_min: "", salary_max: "", linkedin_url: "", github_url: "", portfolio_url: "",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState({ ...blank });
  const [newSkill, setNewSkill] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const p = await api<Profile>("/profile");
    setProfile(p);
    setForm({
      phone: p.phone ?? "", location: p.location ?? "", headline: p.headline ?? "",
      summary: p.summary ?? "", current_role: p.current_role ?? "",
      years_experience: p.years_experience?.toString() ?? "",
      current_ctc: p.current_ctc ?? "", expected_ctc: p.expected_ctc ?? "",
      notice_period: p.notice_period ?? "", work_mode: p.work_mode ?? "any",
      preferred_locations: (p.preferred_locations ?? []).join(", "),
      preferred_titles: (p.preferred_titles ?? []).join(", "),
      salary_min: p.salary_min?.toString() ?? "", salary_max: p.salary_max?.toString() ?? "",
      linkedin_url: p.linkedin_url ?? "", github_url: p.github_url ?? "",
      portfolio_url: p.portfolio_url ?? "",
    });
  }
  useEffect(() => { load(); }, []);

  function set<K extends keyof typeof form>(k: K, v: string) { setForm((f) => ({ ...f, [k]: v })); }
  const toList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  async function save() {
    setSaving(true); setMsg("");
    try {
      await api("/profile", {
        method: "PATCH",
        body: JSON.stringify({
          phone: form.phone || null, location: form.location || null,
          headline: form.headline || null, summary: form.summary || null,
          current_role: form.current_role || null,
          years_experience: form.years_experience ? Number(form.years_experience) : null,
          current_ctc: form.current_ctc || null, expected_ctc: form.expected_ctc || null,
          notice_period: form.notice_period || null, work_mode: form.work_mode,
          preferred_locations: toList(form.preferred_locations),
          preferred_titles: toList(form.preferred_titles),
          salary_min: form.salary_min ? Number(form.salary_min) : null,
          salary_max: form.salary_max ? Number(form.salary_max) : null,
          linkedin_url: form.linkedin_url || null, github_url: form.github_url || null,
          portfolio_url: form.portfolio_url || null,
        }),
      });
      setMsg("Saved ✓"); await load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  }

  async function addSkill() {
    if (!newSkill.trim()) return;
    await api("/profile/skills", { method: "POST", body: JSON.stringify({ name: newSkill.trim() }) });
    setNewSkill(""); await load();
  }
  async function removeSkill(id: string) {
    await api(`/profile/skills/${id}`, { method: "DELETE" }); await load();
  }

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true); setMsg("");
    try {
      const fd = new FormData();
      fd.append("file", file); fd.append("is_master", "true"); fd.append("import_to_profile", "true");
      const t = JSON.parse(localStorage.getItem("jp_tokens") || "{}");
      const res = await fetch(`${API_URL}/resumes/upload`, {
        method: "POST", body: fd, headers: { Authorization: `Bearer ${t.access_token}` },
      });
      if (!res.ok) throw new Error("Upload failed");
      setMsg("Resume parsed & imported ✓"); await load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Upload failed"); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  if (!profile) return <div className="skeleton h-96" />;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your profile</h1>
        <div className="flex items-center gap-3">
          {msg && <span className="text-sm text-slate-500">{msg}</span>}
          <button className="btn-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </div>

      <Section title="Resume">
        <button className="btn-ghost" onClick={() => fileRef.current?.click()} disabled={uploading}>
          {uploading ? "Parsing…" : "Upload resume (PDF/DOCX) — auto-fills skills"}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx" hidden onChange={upload} />
      </Section>

      <Section title="Professional information">
        <Grid>
          <Field label="Current role"><input className="input" value={form.current_role} onChange={(e) => set("current_role", e.target.value)} placeholder="Backend Developer" /></Field>
          <Field label="Years of experience"><input className="input" type="number" step="0.1" value={form.years_experience} onChange={(e) => set("years_experience", e.target.value)} placeholder="2.5" /></Field>
          <Field label="Current CTC"><input className="input" value={form.current_ctc} onChange={(e) => set("current_ctc", e.target.value)} placeholder="6 LPA" /></Field>
          <Field label="Expected CTC"><input className="input" value={form.expected_ctc} onChange={(e) => set("expected_ctc", e.target.value)} placeholder="10 LPA" /></Field>
          <Field label="Notice period"><input className="input" value={form.notice_period} onChange={(e) => set("notice_period", e.target.value)} placeholder="30 days" /></Field>
          <Field label="Location"><input className="input" value={form.location} onChange={(e) => set("location", e.target.value)} placeholder="Tamil Nadu, India" /></Field>
        </Grid>
        <Field label="Headline"><input className="input" value={form.headline} onChange={(e) => set("headline", e.target.value)} placeholder="Python backend developer | FastAPI | AWS" /></Field>
        <Field label="Summary"><textarea className="input min-h-20" value={form.summary} onChange={(e) => set("summary", e.target.value)} /></Field>
      </Section>

      <Section title="Job preferences (drive your matches)">
        <Grid>
          <Field label="Work mode">
            <select className="input" value={form.work_mode} onChange={(e) => set("work_mode", e.target.value)}>
              {["any", "remote", "hybrid", "onsite"].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="Preferred job titles (comma-sep)"><input className="input" value={form.preferred_titles} onChange={(e) => set("preferred_titles", e.target.value)} placeholder="Backend Developer, Python Developer" /></Field>
          <Field label="Preferred locations (comma-sep)"><input className="input" value={form.preferred_locations} onChange={(e) => set("preferred_locations", e.target.value)} placeholder="Remote, Bangalore" /></Field>
          <Field label="Min salary"><input className="input" type="number" value={form.salary_min} onChange={(e) => set("salary_min", e.target.value)} placeholder="800000" /></Field>
          <Field label="Max salary"><input className="input" type="number" value={form.salary_max} onChange={(e) => set("salary_max", e.target.value)} placeholder="1500000" /></Field>
          <Field label="Phone"><input className="input" value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
        </Grid>
      </Section>

      <Section title="Links">
        <Grid>
          <Field label="LinkedIn"><input className="input" value={form.linkedin_url} onChange={(e) => set("linkedin_url", e.target.value)} /></Field>
          <Field label="GitHub"><input className="input" value={form.github_url} onChange={(e) => set("github_url", e.target.value)} /></Field>
          <Field label="Portfolio"><input className="input" value={form.portfolio_url} onChange={(e) => set("portfolio_url", e.target.value)} /></Field>
        </Grid>
      </Section>

      <Section title={`Skills (${profile.skills.length})`}>
        <div className="mb-3 flex flex-wrap gap-2">
          {profile.skills.map((s) => (
            <span key={s.id} className="group flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
              {s.name}
              <button onClick={() => removeSkill(s.id)} className="opacity-50 hover:opacity-100">×</button>
            </span>
          ))}
          {profile.skills.length === 0 && <span className="text-sm text-slate-500">No skills yet — add some or upload a resume.</span>}
        </div>
        <div className="flex gap-2">
          <input className="input" placeholder="Add a skill…" value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addSkill()} />
          <button className="btn-ghost" onClick={addSkill}>Add</button>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card space-y-4">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </div>
  );
}
function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-4 sm:grid-cols-2">{children}</div>;
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-slate-500">{label}</span>
      {children}
    </label>
  );
}
