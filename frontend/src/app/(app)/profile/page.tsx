"use client";
import { useEffect, useRef, useState } from "react";
import { api, API_URL } from "@/lib/api";

interface Skill { id: string; name: string; category: string }
interface Profile {
  id: string; headline?: string; summary?: string; location?: string;
  skills: Skill[]; experiences: unknown[]; projects: unknown[]; educations: unknown[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [newSkill, setNewSkill] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() { setProfile(await api<Profile>("/profile")); }
  useEffect(() => { load(); }, []);

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
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("is_master", "true");
      fd.append("import_to_profile", "true");
      // FormData: let the browser set the multipart boundary
      const tokens = JSON.parse(localStorage.getItem("jp_tokens") || "{}");
      await fetch(`${API_URL}/resumes/upload`, {
        method: "POST", body: fd,
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      await load();
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  if (!profile) return <div className="skeleton h-96" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your profile</h1>
        <button className="btn-primary" onClick={() => fileRef.current?.click()} disabled={uploading}>
          {uploading ? "Parsing resume…" : "Upload resume (PDF/DOCX)"}
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx" hidden onChange={upload} />
      </div>

      <div className="card">
        <h2 className="mb-3 font-semibold">Skills ({profile.skills.length})</h2>
        <div className="mb-3 flex flex-wrap gap-2">
          {profile.skills.map((s) => (
            <span key={s.id} className="group flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700 dark:bg-brand-700/20 dark:text-brand-100">
              {s.name}
              <button onClick={() => removeSkill(s.id)} className="opacity-0 transition group-hover:opacity-100">×</button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input className="input" placeholder="Add a skill…" value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addSkill()} />
          <button className="btn-ghost" onClick={addSkill}>Add</button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Counter label="Experience" n={profile.experiences.length} />
        <Counter label="Projects" n={profile.projects.length} />
        <Counter label="Education" n={profile.educations.length} />
      </div>
    </div>
  );
}

function Counter({ label, n }: { label: string; n: number }) {
  return <div className="card"><p className="text-sm text-slate-500">{label}</p><p className="text-2xl font-bold">{n}</p></div>;
}
