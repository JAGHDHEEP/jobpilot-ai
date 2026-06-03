export interface User {
  id: string; email: string; full_name: string; role: "user" | "admin";
  is_active: boolean; is_verified: boolean;
}

export interface Job {
  id: string; title: string; company: string; location?: string;
  remote_type?: string; salary_min?: number; salary_max?: number; currency?: string;
  description: string; requirements: string[]; keywords: string[];
  experience_min?: number; posted_at?: string; apply_url?: string; source: string;
}

export interface Match {
  id: string; job_id: string; overall_score: number;
  skill_score: number; project_score: number; experience_score: number;
  education_score: number; keyword_score: number;
  missing_skills: string[]; missing_keywords: string[]; rationale?: string;
}

export interface MatchWithJob { match: Match; job: Job }

export interface Recommendation { rank: number; rank_score: number; job: Job; match?: Match }

export interface Application {
  id: string; job_id: string; status: string; notes?: string;
  applied_at?: string; created_at: string;
  events: { to_status: string; from_status?: string; note?: string; created_at: string }[];
}

export interface Analytics {
  funnel: Record<string, number>; per_month: Record<string, number>;
  success_rate: number; interview_rate: number; total: number;
}
