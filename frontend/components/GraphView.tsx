import { useMemo, useCallback } from "react";
import {
  ReactFlow, Background,
  type Node, type Edge,
  type Viewport,
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

const COL_WIDTH = 240;
const ROW_HEIGHT = 130;

function flattenNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.flatMap((n) => [n, ...flattenNodes(n.children)]);
}

function computePositions(roots: TreeNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  let leaf = 0;

  function place(node: TreeNode): number {
    if (node.children.length === 0) {
      const col = leaf++;
      positions.set(node.id, { x: col * COL_WIDTH, y: node.depth * ROW_HEIGHT });
      return col;
    }
    const childCols = node.children.map(place);
    const col = (childCols[0] + childCols[childCols.length - 1]) / 2;
    positions.set(node.id, { x: col * COL_WIDTH, y: node.depth * ROW_HEIGHT });
    return col;
  }

  roots.forEach(place);
  return positions;
}

const ROOT_ID = "__query_root__";

interface GraphViewProps {
  rootNodes: TreeNode[];
  selectedId: string | null;
  onSelect: (node: TreeNode) => void;
  query?: string | null;
}

export function GraphView({ rootNodes, selectedId, onSelect, query }: GraphViewProps) {
  const { rfNodes, rfEdges, rootX } = useMemo(() => {
    const all = flattenNodes(rootNodes);
    const positions = computePositions(rootNodes);

    const rfNodes: any[] = all.map((n) => ({
      id: n.id,
      position: positions.get(n.id) ?? { x: 0, y: 0 },
      data: {
        label: (
          <div className={styles.nodeLabel}>
            <span className={styles.nodeStatus} style={{ color: STATUS_COLOR[n.status] }}>
              {n.status === "complete" ? "✓" : "⟳"}
            </span>
            <span className={styles.nodeQuestion}>
              {n.question.slice(0, 70)}{n.question.length > 70 ? "…" : ""}
            </span>
          </div>
        ),
        treeNode: n,
      },
      style: {
        background: "#ece6d8",
        border: `1px solid ${selectedId === n.id ? "#3d6b4a" : "#d4c8b4"}`,
        borderRadius: "4px",
        color: "#2a2418",
        fontSize: "11px",
        width: 200,
      },
    }));

    let rootX = 0;
    if (query) {
      const xs = rootNodes.map((n) => positions.get(n.id)?.x ?? 0);
      rootX = xs.length ? (Math.min(...xs) + Math.max(...xs)) / 2 : 0;
      rfNodes.unshift({
        id: ROOT_ID,
        position: { x: rootX, y: -ROW_HEIGHT },
        data: {
          label: (
            <div className={styles.nodeLabel}>
              <span className={styles.nodeQuestion}>
                {query.slice(0, 70)}{query.length > 70 ? "…" : ""}
              </span>
            </div>
          ),
        },
        style: {
          background: "#3d6b4a",
          border: "1px solid #2a4d34",
          borderRadius: "4px",
          color: "#f5f0e8",
          fontSize: "11px",
          fontWeight: 600,
          width: 200,
        },
      });
    }

    const rfEdges: any[] = all
      .filter((n) => n.parentId && n.parentId !== "root")
      .map((n) => ({
        id: `${n.parentId}-${n.id}`,
        source: n.parentId!,
        target: n.id,
        style: { stroke: "#d4c8b4" },
        animated: n.status !== "complete",
      }));

    if (query) {
      rootNodes.forEach((n) => {
        rfEdges.push({
          id: `${ROOT_ID}-${n.id}`,
          source: ROOT_ID,
          target: n.id,
          style: { stroke: "#d4c8b4" },
          animated: n.status !== "complete",
        });
      });
    }

    return { rfNodes, rfEdges, rootX };
  }, [rootNodes, selectedId, query]);

  // Calculate initial viewport to center on root node
  const initialViewport = useMemo<Viewport | undefined>(() => {
    if (rootNodes.length === 0) return undefined;
    // Center on the root area around rootX, with a reasonable zoom
    return {
      x: rootX - 300,
      y: -200,
      zoom: 0.6,
    };
  }, [rootX, rootNodes.length]);

  const handleNodeClick = useCallback(
    (_, node: any) => onSelect((node.data as { treeNode: TreeNode }).treeNode),
    [onSelect]
  );

  return (
    <div className={styles.container}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ maxZoom: 2, minZoom: 0.1 }}
        defaultViewport={initialViewport}
        colorMode="light"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e0d8c8" gap={16} />
      </ReactFlow>
    </div>
  );
}
