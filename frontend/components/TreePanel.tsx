"use client";
import type { TreeNode } from "@/lib/types";
import styles from "./TreePanel.module.css";

const STATUS_INDICATOR: Record<TreeNode["status"], string> = {
  pending: "○",
  searching: "⟳",
  reflecting: "⟳",
  spawning: "⟳",
  complete: "✓",
  error: "✕",
};

interface TreePanelProps {
  nodes: TreeNode[];
  selectedId: string | null;
  onSelect: (node: TreeNode) => void;
}

function TreeRow({
  node,
  selectedId,
  onSelect,
}: {
  node: TreeNode;
  selectedId: string | null;
  onSelect: (node: TreeNode) => void;
}) {
  const isActive = ["searching", "reflecting", "spawning"].includes(node.status);
  return (
    <div className={styles.nodeWrap}>
      <div
        className={`${styles.row} ${selectedId === node.id ? styles.selected : ""}`}
        onClick={() => onSelect(node)}
      >
        <span
          key={node.status}
          className={`${styles.indicator} ${styles[node.status]} ${isActive ? styles.pulse : ""}`}
        >
          {STATUS_INDICATOR[node.status]}
        </span>
        <span className={styles.label}>{node.question}</span>
        {node.status === "complete" && (
          <span className={styles.meta}>{node.sources.length}s</span>
        )}
      </div>
      {node.children.length > 0 && (
        <div className={styles.children}>
          {node.children.map((child) => (
            <TreeRow key={child.id} node={child} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

export function TreePanel({ nodes, selectedId, onSelect }: TreePanelProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.header}>Research Tree</div>
      {nodes.map((node) => (
        <TreeRow key={node.id} node={node} selectedId={selectedId} onSelect={onSelect} />
      ))}
    </div>
  );
}
