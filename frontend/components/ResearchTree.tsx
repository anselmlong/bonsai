"use client";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { AnswerRenderer } from "./AnswerRenderer";
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

type Phase = "researching" | "banner" | "summary";
type ActiveTab = "summary" | "graph" | "tree";

interface ResearchTreeProps {
  jobId: string;
}

export function ResearchTree({ jobId }: ResearchTreeProps) {
  const { events, done } = useResearchStream(jobId);
  const { rootNodes, nodeMap, finalAnswer } = useResearchTree(events);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("researching");
  const [activeTab, setActiveTab] = useState<ActiveTab>("summary");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (finalAnswer && phase === "researching") {
      setPhase("banner");
    }
  }, [finalAnswer, phase]);

  const handleCopy = () => {
    if (!finalAnswer) return;
    const plain = finalAnswer
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "")
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
    navigator.clipboard.writeText(plain).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const selected = selectedId ? (nodeMap.get(selectedId) ?? null) : null;

  const allNodes = [...nodeMap.values()];
  const completeCount = allNodes.filter((n) => n.status === "complete").length;
  const sourceCount = allNodes.reduce((sum, n) => sum + n.sources.length, 0);
  const maxDepth = allNodes.reduce((max, n) => Math.max(max, n.depth), 0);

  const handleSelect = (node: TreeNode) =>
    setSelectedId((prev) => (prev === node.id ? null : node.id));

  const handleDismissBanner = () => {
    setPhase("summary");
    setActiveTab("summary");
  };

  return (
    <div className={styles.shell}>
      <nav className={styles.nav}>
        <a href="/" className={styles.logo}>b<span>o</span>nsai</a>
        <span className={styles.navSep} />
        <QueryInput variant="nav" />
        <div className={styles.navSpacer} />
      </nav>

      {phase === "summary" ? (
        <div className={styles.summaryLayout}>
          <div className={styles.tabBar}>
            <button
              className={`${styles.tabBtn} ${activeTab === "summary" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("summary")}
            >
              Summary
            </button>
            <button
              className={`${styles.tabBtn} ${activeTab === "graph" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("graph")}
            >
              Research Graph
            </button>
            <button
              className={`${styles.tabBtn} ${activeTab === "tree" ? styles.tabBtnActive : ""}`}
              onClick={() => setActiveTab("tree")}
            >
              Tree
            </button>
          </div>

          <div className={styles.tabContent}>
            {/* Summary tab */}
            <div className={`${styles.tabPanel} ${activeTab === "summary" ? styles.tabPanelActive : ""}`}>
              <div className={styles.detail}>
                {selected ? (
                  <>
                    <div className={styles.backBar}>
                      <button className={styles.backBtn} onClick={() => setSelectedId(null)}>
                        ← Summary
                      </button>
                    </div>
                    <NodeDetail node={selected} onSelect={handleSelect} />
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
                      <AnswerRenderer content={finalAnswer} />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            {/* Graph tab */}
            <div className={`${styles.tabPanel} ${activeTab === "graph" ? styles.tabPanelActive : ""}`}>
              <div className={styles.graphTabContainer}>
                <GraphView rootNodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
                {selected && (
                  <div className={styles.graphDetailPane}>
                    <NodeDetail node={selected} onSelect={handleSelect} />
                  </div>
                )}
              </div>
            </div>

            {/* Tree tab */}
            <div className={`${styles.tabPanel} ${activeTab === "tree" ? styles.tabPanelActive : ""}`}>
              <div className={styles.main}>
                <TreePanel nodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
                <div className={styles.detail}>
                  {selected ? (
                    <>
                      <div className={styles.backBar}>
                        <button className={styles.backBtn} onClick={() => setSelectedId(null)}>
                          ← Summary
                        </button>
                      </div>
                      <NodeDetail node={selected} onSelect={handleSelect} />
                    </>
                  ) : (
                    <div className={styles.placeholder}>
                      <span className={styles.placeholderArrow}>←</span>
                      Select a branch to inspect it
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className={styles.graphStage}>
          <GraphView rootNodes={rootNodes} selectedId={selectedId} onSelect={handleSelect} />
          {selected && (
            <div className={styles.graphDetailPane}>
              <NodeDetail node={selected} onSelect={handleSelect} />
            </div>
          )}
          {phase === "banner" && (
            <div className={styles.banner}>
              <span className={styles.bannerText}>Summary ready</span>
              <button className={styles.bannerBtn} onClick={handleDismissBanner}>
                View results →
              </button>
            </div>
          )}
        </div>
      )}

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
