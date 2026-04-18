"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("tree");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!finalAnswer) return;
    navigator.clipboard.writeText(finalAnswer).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const selected = selectedId ? (nodeMap.get(selectedId) ?? null) : null;

  const allNodes = [...nodeMap.values()];
  const completeCount = allNodes.filter((n) => n.status === "complete").length;
  const sourceCount = allNodes.reduce((sum, n) => sum + n.sources.length, 0);
  const maxDepth = allNodes.reduce((max, n) => Math.max(max, n.depth), 0);

  const handleSelect = (node: TreeNode) => setSelectedId((prev) => (prev === node.id ? null : node.id));

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
            <TreePanel nodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
            <div className={styles.detail}>
              {selected ? (
                <>
                  {finalAnswer && (
                    <div className={styles.backBar}>
                      <button className={styles.backBtn} onClick={() => setSelectedId(null)}>
                        ← Summary
                      </button>
                    </div>
                  )}
                  <NodeDetail node={selected} jobId={jobId} allNodes={nodeMap} onSelect={handleSelect} />
                </>
              ) : finalAnswer ? (
                <div className={styles.answer}>
                  <div className={styles.answerHeader}>
                    <div className={styles.answerLabel}>Final Answer</div>
                    <button
                      className={`${styles.copyBtn} ${copied ? styles.copied : ""}`}
                      onClick={handleCopy}
                    >
                      {copied ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <div className={styles.answerText}>
                    <ReactMarkdown>{finalAnswer}</ReactMarkdown>
                  </div>
                </div>
              ) : (
                <div className={styles.placeholder}>
                  <span className={styles.placeholderArrow}>←</span>
                  Select a branch to inspect it
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            <GraphView rootNodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
            {selected && (
              <div className={styles.graphDetailPane}>
                <NodeDetail node={selected} jobId={jobId} allNodes={nodeMap} onSelect={handleSelect} />
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
