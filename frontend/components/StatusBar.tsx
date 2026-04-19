import styles from "./StatusBar.module.css";

interface StatusBarProps {
  done: boolean;
  branchCount: number;
  completeCount: number;
  sourceCount: number;
  maxDepthReached: number;
  langsmithUrl?: string;
  synthesizing: boolean;
}

export function StatusBar({
  done, branchCount, completeCount, sourceCount, maxDepthReached, langsmithUrl, synthesizing,
}: StatusBarProps) {
  return (
    <div className={styles.bar}>
      {!done ? (
        <>
          <span className={styles.dot} />
          {synthesizing ? (
            <>
              <span className={styles.active}>Synthesizing</span>
              <span className={styles.spinningDot}>⟳</span>
            </>
          ) : (
            <span className={styles.active}>Researching</span>
          )}
        </>
      ) : (
        <span className={styles.done}>Complete</span>
      )}
      <span className={styles.sep}>·</span>
      <span>{completeCount} / {branchCount} branches</span>
      <span className={styles.sep}>·</span>
      <span>{sourceCount} sources</span>
      <span className={styles.sep}>·</span>
      <span>depth {maxDepthReached}</span>
      {langsmithUrl && (
        <a href={langsmithUrl} target="_blank" rel="noopener" className={styles.trace}>
          langsmith trace ↗
        </a>
      )}
    </div>
  );
}
