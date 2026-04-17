import type { Source } from "@/lib/types";
import styles from "./SourceCard.module.css";

export function SourceCard({ source }: { source: Source }) {
  return (
    <a href={source.url} target="_blank" rel="noopener" className={styles.card}>
      <div className={styles.top}>
        <span className={styles.domain}>
          {new URL(source.url).hostname.replace("www.", "")}
        </span>
        <span className={styles.score}>{source.score.toFixed(2)}</span>
      </div>
      <div className={styles.title}>{source.title}</div>
      {source.excerpt && (
        <blockquote className={styles.excerpt}>{source.excerpt}</blockquote>
      )}
    </a>
  );
}
