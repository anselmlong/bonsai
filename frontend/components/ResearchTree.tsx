"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { useResearchStream } from "@/hooks/useResearchStream";
import { useResearchTree } from "@/hooks/useResearchTree";
import { TreePanel } from "./TreePanel";
import { NodeDetail } from "./NodeDetail";
import { StatusBar } from "./StatusBar";
import { QueryInput } from "./QueryInput";
import type { TreeNode } from "@/lib/types";
import styles from "./ResearchTree.module.css";

const GraphView = dynamic(() => import("./GraphView").then((m) => m.GraphView), {
  ssr: false,
});

type ViewMode = "tree" | "graph";

interface ResearchTreeProps {
  jobId: string;
}

export function ResearchTree({ jobId }: ResearchTreeProps) {
  const { events, done } = useResearchStream(jobId);
  const { rootNodes, nodeMap, finalAnswer } = useResearchTree(events);
  const [selected, setSelected] = useState<TreeNode | null>(null);
  const [view, setView] = useState<ViewMode>("tree");

  const allNodes = [...nodeMap.values()];
  const completeCount = allNodes.filter((n) => n.status === "complete").length;
  const sourceCount = allNodes.reduce((sum, n) => sum + n.sources.length, 0);
  const maxDepth = allNodes.reduce((max, n) => Math.max(max, n.depth), 0);

  return (
    <div className={styles.shell}>
      <nav className={styles.nav}>
        <span className={styles.logo}>b<span>o</span>nsai</span>
        <span className={styles.navSep} />
        <QueryInput variant="nav" />
        <div className={styles.navSpacer} />
        <div className={styles.toggle}>
          <button
            className={`${styles.toggleBtn} ${view === "tree" ? styles.active : ""}`}
            onClick={() => setView("tree")}
          >⊞ TREE</button>
          <button
            className={`${styles.toggleBtn} ${view === "graph" ? styles.active : ""}`}
            onClick={() => setView("graph")}
          >◈ GRAPH</button>
        </div>
      </nav>

      <div className={styles.main}>
        {view === "tree" ? (
          <>
            <TreePanel nodes={rootNodes} selectedId={selected?.id ?? null} onSelect={setSelected} />
            <div className={styles.detail}>
              {selected ? (
                <NodeDetail node={selected} jobId={jobId} allNodes={nodeMap} onSelect={setSelected} />
              ) : finalAnswer ? (
                <div className={styles.answer}>
                  <div className={styles.answerLabel}>Final Answer</div>
                  <p className={styles.answerText}>{finalAnswer}</p>
                </div>
              ) : (
                <div className={styles.placeholder}>Select a branch to inspect it.</div>
              )}
            </div>
          </>
        ) : (
          <>
            <GraphView rootNodes={rootNodes} selectedId={selected?.id ?? null} onSelect={setSelected} />
            {selected && (
              <div className={styles.graphDetailPane}>
                <NodeDetail node={selected} jobId={jobId} allNodes={nodeMap} onSelect={setSelected} />
              </div>
            )}
          </>
        )}
      </div>

      <StatusBar
        done={done}
        branchCount={allNodes.length}
        completeCount={completeCount}
        sourceCount={sourceCount}
        maxDepthReached={maxDepth}
      />
    </div>
  );
}
