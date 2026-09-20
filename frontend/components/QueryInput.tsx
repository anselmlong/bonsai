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
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) {
        setError(res.status === 429 ? "All research slots are busy. Please try again shortly." : "Research could not start. Please try again.");
        return;
      }
      const { job_id } = await res.json();
      if (typeof job_id !== "string" || !/^[a-f0-9]{32}$/.test(job_id)) {
        setError("The server returned an invalid research session. Please try again.");
        return;
      }
      router.push(`/research/${job_id}`);
    } catch {
      setError("Could not reach the research service. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isNav = variant === "nav";

  return (
    <>
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
        maxLength={4000}
        aria-label="Research question"
      />
      <button
        className={`${styles.btn} ${isNav ? styles.btnNav : styles.btnHero} ${loading ? styles.loading : ""}`}
        type="submit"
        disabled={loading}
        aria-label={loading ? "Starting research" : "Start research"}
      >
        {loading ? "→" : "→"}
      </button>
    </form>
    {error && <p role="alert">{error}</p>}
    </>
  );
}
