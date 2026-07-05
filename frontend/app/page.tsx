"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiHealth } from "@/lib/api";
import { SectionCard } from "@/components/ui/Card";

const tiles = [
  {
    href: "/upload",
    title: "เพิ่มเสื้อผ้า",
    desc: "ถ่ายหรืออัปโหลด · วิเคราะห์สไตล์ด้วย AI",
    emoji: "📷",
    gradient: true,
  },
  {
    href: "/closet",
    title: "ตู้เสื้อผ้า",
    desc: "ดูและจัดการทุกชิ้น",
    emoji: "👗",
  },
  {
    href: "/match",
    title: "จับคู่ชุด",
    desc: "เลือกบน + ล่าง รับคะแนนความเข้ากัน",
    emoji: "✨",
  },
  {
    href: "/recommend",
    title: "แนะนำตามที่",
    desc: "ทะเล วัด ออฟฟิศ งานเลี้ยง",
    emoji: "📍",
  },
] as const;

export default function HomePage() {
  const [api, setApi] = useState<{ ok: boolean; text: string }>({
    ok: false,
    text: "กำลังเช็ค…",
  });

  useEffect(() => {
    apiHealth().then((r) =>
      setApi({
        ok: r.ok,
        text: r.ok ? (r.message ?? "พร้อมใช้งาน") : (r.message ?? "ไม่พร้อม"),
      }),
    );
  }, []);

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-500">
          Outfit matching
        </p>
        <h1 className="font-display text-3xl leading-tight text-stone-900 dark:text-stone-50 sm:text-4xl">
          Next Day
        </h1>
        <p className="max-w-md text-[15px] leading-relaxed text-stone-600 dark:text-stone-400">
          ตู้เสื้อผ้าดิจิตอล — จัดชุด จับคู่ และแนะนำตามโอกาสในที่เดียว
        </p>
        <div
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
            api.ok
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300"
              : "bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${api.ok ? "bg-emerald-500" : "bg-amber-500"}`} />
          API: {api.text}
        </div>
      </header>

      <SectionCard title="เริ่มใช้งาน" description="เลือกขั้นตอนถัดไป">
        <div className="grid gap-3 sm:grid-cols-2">
          {tiles.map((t) =>
            "gradient" in t && t.gradient ? (
              <Link
                key={t.href}
                href={t.href}
                className="group relative col-span-full overflow-hidden rounded-2xl bg-gradient-to-br from-rose-500 via-rose-500 to-orange-400 p-5 text-white shadow-lg shadow-rose-500/25 transition hover:brightness-105 active:scale-[0.99] sm:col-span-2"
              >
                <span className="text-3xl">{t.emoji}</span>
                <p className="mt-2 font-display text-2xl">{t.title}</p>
                <p className="mt-1 text-sm text-white/85">{t.desc}</p>
                <span className="mt-3 inline-flex items-center text-sm font-semibold">
                  เริ่มเลย
                  <span className="ml-1 transition group-hover:translate-x-0.5">→</span>
                </span>
              </Link>
            ) : (
              <Link
                key={t.href}
                href={t.href}
                className="flex flex-col rounded-2xl border border-stone-100 bg-stone-50/80 p-4 transition hover:border-rose-200 hover:bg-white hover:shadow-md dark:border-stone-800 dark:bg-stone-900/50 dark:hover:border-rose-900"
              >
                <span className="text-2xl">{t.emoji}</span>
                <p className="mt-2 font-semibold text-stone-900 dark:text-stone-100">{t.title}</p>
                <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">{t.desc}</p>
              </Link>
            ),
          )}
        </div>
      </SectionCard>

      <SectionCard title="แผนโปรเจค (สรุป)" description="จากเอกสาร Notion">
        <div className="overflow-hidden rounded-2xl border border-stone-100 dark:border-stone-800">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-stone-100 bg-stone-50/80 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:border-stone-800 dark:bg-stone-900/80 dark:text-stone-400">
                <th className="px-3 py-2">เฟส</th>
                <th className="px-3 py-2">หัวข้อ</th>
                <th className="hidden px-3 py-2 sm:table-cell">สถานะเดโม</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
              {[
                ["1", "Setup & tools", "Next + FastAPI"],
                ["2", "Fashion classify", "EfficientNet + YOLO"],
                ["3", "ตู้เสื้อผ้า", "In-memory"],
                ["4", "จับคู่ + สถานที่", "พร้อมใช้"],
                ["5", "Deploy", "ภายหลัง"],
              ].map(([phase, title, status]) => (
                <tr key={phase} className="text-stone-700 dark:text-stone-300">
                  <td className="px-3 py-2.5 font-mono text-xs text-rose-600 dark:text-rose-400">
                    {phase}
                  </td>
                  <td className="px-3 py-2.5">{title}</td>
                  <td className="hidden px-3 py-2.5 text-stone-500 sm:table-cell">{status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4">
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-2xl border border-stone-200 bg-white px-3.5 py-2 text-sm font-medium text-stone-800 shadow-sm transition hover:border-rose-200 hover:bg-rose-50/50 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:hover:border-rose-800"
          >
            เปิด API docs ↗
          </a>
        </div>
        <p className="mt-2 text-xs text-stone-400">
          ลิงก์ docs ใช้เมื่อรัน backend ที่พอร์ต 8000
        </p>
      </SectionCard>
    </div>
  );
}
