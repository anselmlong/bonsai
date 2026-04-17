"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./QueryInput.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface QueryInputProps {
  variant: "hero" | "nav";
}

export function QueryInput({ variant }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const { job_id } = await res.json();
      router.push(`/research/${job_id}`);
    } catch {
      setLoading(false);
    }
  };

  const isNav = variant === "nav";

  return (
    <form
      className={`${styles.form} ${isNav ? styles.formNav : styles.formHero}`}
      onSubmit={handleSubmit}
    >
      <input
        className={`${styles.input} ${isNav ? styles.inputNav : styles.inputHero}`}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={isNav ? "New research query…" : "What do you want to research?"}
        autoFocus={!isNav}
      />
      <button
        className={`${styles.btn} ${isNav ? styles.btnNav : styles.btnHero}`}
        type="submit"
        disabled={loading}
      >
        {loading ? "…" : "→"}
      </button>
    </form>
  );
}
