import { useMemo } from "react";
import type { NodeEvent, TreeNode, NodeStatus } from "@/lib/types";

const STATUS_MAP: Partial<Record<NodeEvent["type"], NodeStatus>> = {
  branch_started: "pending",
  branch_searching: "searching",
  branch_reflecting: "reflecting",
  branch_spawning: "spawning",
  branch_complete: "complete",
};

export function useResearchTree(events: NodeEvent[]): {
  rootNodes: TreeNode[];
  nodeMap: Map<string, TreeNode>;
  finalAnswer: string | null;
} {
  return useMemo(() => {
    const nodeMap = new Map<string, TreeNode>();
    let finalAnswer: string | null = null;

    for (const event of events) {
      if (event.type === "research_complete") {
        finalAnswer = event.answer;
        continue;
      }

      const newStatus = STATUS_MAP[event.type];
      if (!newStatus && event.type !== "branch_complete") continue;

      const existing = nodeMap.get(event.node_id);

      if (!existing) {
        nodeMap.set(event.node_id, {
          id: event.node_id,
          parentId: event.parent_id,
          question: event.question ?? "",
          depth: event.depth,
          status: newStatus ?? "pending",
          sources: event.sources ?? [],
          summary: event.summary ?? "",
          children: [],
        });
      } else {
        if (newStatus) existing.status = newStatus;
        if (event.type === "branch_complete") {
          existing.sources = event.sources ?? existing.sources;
          existing.summary = event.summary ?? existing.summary;
          existing.status = "complete";
        }
      }
    }

    // Wire up children
    const rootNodes: TreeNode[] = [];
    for (const node of nodeMap.values()) {
      if (node.parentId && node.parentId !== "root") {
        const parent = nodeMap.get(node.parentId);
        if (parent && !parent.children.find((c) => c.id === node.id)) {
          parent.children.push(node);
        }
      } else {
        if (!rootNodes.find((n) => n.id === node.id)) {
          rootNodes.push(node);
        }
      }
    }

    return { rootNodes, nodeMap, finalAnswer };
  }, [events]);
}
