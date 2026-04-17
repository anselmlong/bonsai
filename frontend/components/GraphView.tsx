"use client";
import { useMemo } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  type Node, type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { TreeNode } from "@/lib/types";
import styles from "./GraphView.module.css";

const STATUS_COLOR: Record<TreeNode["status"], string> = {
  pending: "#374151",
  searching: "oklch(72% 0.12 95)",
  reflecting: "oklch(72% 0.12 95)",
  spawning: "oklch(72% 0.12 95)",
  complete: "oklch(68% 0.14 155)",
  error: "oklch(62% 0.14 25)",
};

function flattenNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.flatMap((n) => [n, ...flattenNodes(n.children)]);
}

interface GraphViewProps {
  rootNodes: TreeNode[];
  selectedId: string | null;
  onSelect: (node: TreeNode) => void;
}

export function GraphView({ rootNodes, selectedId, onSelect }: GraphViewProps) {
  const { rfNodes, rfEdges } = useMemo(() => {
    const all = flattenNodes(rootNodes);
    const rfNodes: Node[] = all.map((n, i) => ({
      id: n.id,
      position: { x: (i % 4) * 220, y: n.depth * 140 },
      data: {
        label: (
          <div className={styles.nodeLabel}>
            <span className={styles.nodeStatus} style={{ color: STATUS_COLOR[n.status] }}>
              {n.status === "complete" ? "✓" : "⟳"}
            </span>
            <span className={styles.nodeQuestion}>{n.question.slice(0, 70)}{n.question.length > 70 ? "…" : ""}</span>
          </div>
        ),
        treeNode: n,
      },
      style: {
        background: "oklch(18% 0.010 250)",
        border: `1px solid ${selectedId === n.id ? "oklch(72% 0.12 95)" : "oklch(28% 0.010 250)"}`,
        borderRadius: "6px",
        color: "oklch(92% 0.008 250)",
        fontSize: "11px",
        width: 220,
      },
    }));

    const rfEdges: Edge[] = all
      .filter((n) => n.parentId && n.parentId !== "root")
      .map((n) => ({
        id: `${n.parentId}-${n.id}`,
        source: n.parentId!,
        target: n.id,
        style: { stroke: "oklch(28% 0.010 250)" },
        animated: n.status !== "complete",
      }));

    return { rfNodes, rfEdges };
  }, [rootNodes, selectedId]);

  return (
    <div className={styles.container}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={(_, node) => onSelect((node.data as { treeNode: TreeNode }).treeNode)}
        fitView
        colorMode="dark"
      >
        <Background color="oklch(22% 0.010 250)" gap={16} />
        <Controls />
        <MiniMap nodeColor={(n) => STATUS_COLOR[(n.data as { treeNode: TreeNode }).treeNode.status]} />
      </ReactFlow>
    </div>
  );
}
