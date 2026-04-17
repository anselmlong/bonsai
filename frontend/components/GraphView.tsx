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
  pending: "#c0b8a8",
  searching: "#3d6b4a",
  reflecting: "#3d6b4a",
  spawning: "#3d6b4a",
  complete: "#3d6b4a",
  error: "#8b3a2a",
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
        background: "#ece6d8",
        border: `1px solid ${selectedId === n.id ? "#3d6b4a" : "#d4c8b4"}`,
        borderRadius: "6px",
        color: "#2a2418",
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
        style: { stroke: "#d4c8b4" },
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
        colorMode="light"
      >
        <Background color="#e0d8c8" gap={16} />
        <Controls />
        <MiniMap nodeColor={(n) => STATUS_COLOR[(n.data as { treeNode: TreeNode }).treeNode.status]} />
      </ReactFlow>
    </div>
  );
}
