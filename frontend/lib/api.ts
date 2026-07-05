import { DEMO_USER_ID } from "@/lib/constants";

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

export type ClothesItem = {
  id: string;
  user_id: string;
  image_url: string;
  category: string;
  color: string;
  style: string;
  name?: string;
  embedding: null;
  created_at: string;
};

export type LocationItem = {
  id: string;
  name: string;
  slug: string;
  dress_code: { style: string[]; avoid?: string[] };
  gender: string;
};

export async function apiHealth(): Promise<{ ok: boolean; message?: string }> {
  try {
    const r = await fetch(`${getApiBase()}/health`, { cache: "no-store" });
    if (!r.ok) return { ok: false, message: `HTTP ${r.status}` };
    return { ok: true, message: "API พร้อม" };
  } catch {
    return { ok: false, message: "เชื่อม API ไม่ได้ — รัน uvicorn ที่ port 8000" };
  }
}

export async function fetchClothes(userId = DEMO_USER_ID): Promise<ClothesItem[]> {
  const r = await fetch(
    `${getApiBase()}/clothes?user_id=${encodeURIComponent(userId)}`,
    { cache: "no-store" },
  );
  if (!r.ok) throw new Error("GET /clothes failed");
  const j = (await r.json()) as { items: ClothesItem[] };
  return j.items ?? [];
}

export async function createClothes(form: FormData): Promise<ClothesItem> {
  const r = await fetch(`${getApiBase()}/clothes`, {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "POST /clothes failed");
  }
  return r.json() as Promise<ClothesItem>;
}

export type ClassifyLabel = {
  id: string;
  th: string;
  en: string;
  icon: string;
  color: string;
  probability: number;
  is_positive: boolean;
  percent: number;
};

export type ClassifyResult = {
  success: boolean;
  yolo_detected: boolean;
  original_size: [number, number];
  cropped_size: [number, number];
  labels: ClassifyLabel[];
  top_label: ClassifyLabel | null;
  occasion: string;
  style: string;
  confidence: number;
  model: string;
};

export async function classifyImage(file: File): Promise<ClassifyResult> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${getApiBase()}/classify`, { method: "POST", body: fd });
  if (!r.ok) throw new Error("POST /classify failed");
  return r.json() as Promise<ClassifyResult>;
}

export async function matchOutfit(
  topId: string,
  bottomId: string,
  userId = DEMO_USER_ID,
): Promise<{
  score: number;
  score_percent: number;
  note: string;
}> {
  const r = await fetch(`${getApiBase()}/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, top_id: topId, bottom_id: bottomId }),
  });
  if (!r.ok) throw new Error("POST /match failed");
  return r.json() as Promise<{
    score: number;
    score_percent: number;
    note: string;
  }>;
}

export async function fetchLocations(): Promise<LocationItem[]> {
  const r = await fetch(`${getApiBase()}/locations`, { cache: "no-store" });
  if (!r.ok) throw new Error("GET /locations failed");
  const j = (await r.json()) as { items: LocationItem[] };
  return j.items ?? [];
}

export async function fetchRecommend(
  location: string,
  gender: string,
  userId = DEMO_USER_ID,
): Promise<{
  top: ClothesItem;
  bottom: ClothesItem;
  score_percent: number;
  location: { name: string; slug: string };
}> {
  const q = new URLSearchParams({
    location,
    gender,
    user_id: userId,
  });
  const r = await fetch(`${getApiBase()}/recommend?${q}`, { cache: "no-store" });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "GET /recommend failed");
  }
  return r.json() as Promise<{
    top: ClothesItem;
    bottom: ClothesItem;
    score_percent: number;
    location: { name: string; slug: string };
  }>;
}

export async function deleteClothes(id: string, userId = DEMO_USER_ID): Promise<void> {
  const r = await fetch(
    `${getApiBase()}/clothes/${id}?user_id=${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
  if (!r.ok) throw new Error("DELETE failed");
}
