"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    const res = await fetch(`${API_BASE}/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const { job_id } = await res.json();
    router.push(`/research/${job_id}`);
  };

  return (
    <main className={styles.main}>
      <h1 className={styles.logo}>b<span>o</span>nsai</h1>
      <p className={styles.sub}>deep research, every branch visible</p>
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What do you want to research?"
          autoFocus
        />
        <button className={styles.btn} type="submit" disabled={loading}>
          {loading ? "starting…" : "RESEARCH →"}
        </button>
      </form>
    </main>
  );
}
