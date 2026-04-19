"use client";
import type { TreeNode } from "@/lib/types";
import { SourceCard } from "./SourceCard";
import styles from "./NodeDetail.module.css";

interface NodeDetailProps {
  node: TreeNode;
  onSelect: (node: TreeNode) => void;
}

export function NodeDetail({ node, onSelect }: NodeDetailProps) {
  const subNodes = node.children;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div>
          <div className={styles.badge}>
            Branch · Depth {node.depth} · {node.status}
          </div>
          <h2 className={styles.title}>{node.question}</h2>
        </div>
      </div>

      {node.summary && (
        <section className={styles.section}>
          <div className={styles.label}>Summary</div>
          <p className={styles.summary}>{node.summary}</p>
        </section>
      )}

      {subNodes.length > 0 && (
        <section className={styles.section}>
          <div className={styles.label}>Sub-questions explored</div>
          <div className={styles.subqList}>
            {subNodes.map((child) => (
              <button
                key={child.id}
                className={styles.subqItem}
                onClick={() => onSelect(child)}
              >
                ↳ {child.question}
              </button>
            ))}
          </div>
        </section>
      )}

      {node.sources.length > 0 && (
        <section className={styles.section}>
          <div className={styles.label}>Sources ({node.sources.length})</div>
          <div className={styles.sourceList}>
            {node.sources.map((s) => (
              <SourceCard key={s.url} source={s} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
