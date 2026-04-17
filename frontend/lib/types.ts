// Mirrors backend/models/types.py exactly

export type NodeEventType =
  | "research_started"
  | "plan_complete"
  | "branch_started"
  | "branch_searching"
  | "branch_reflecting"
  | "branch_spawning"
  | "branch_complete"
  | "synthesis_started"
  | "research_complete"
  | "error";

export interface Source {
  url: string;
  title: string;
  excerpt: string;
  score: number;
}

export interface BranchResult {
  node_id: string;
  question: string;
  summary: string;
  sources: Source[];
  depth: number;
}

export interface NodeEvent {
  type: NodeEventType;
  node_id: string;
  parent_id: string | null;
  depth: number;
  question: string | null;
  sources: Source[] | null;
  summary: string | null;
  answer: string | null;
  timestamp: number;
}

export interface ResearchConfig {
  max_branches?: number;
  max_depth?: number;
  planner_model?: string;
  researcher_model?: string;
  synthesizer_model?: string;
  tavily_max_results?: number;
}

// Frontend-only: enriched tree node built from NodeEvent stream
export type NodeStatus =
  | "pending"
  | "searching"
  | "reflecting"
  | "spawning"
  | "complete"
  | "error";

export interface TreeNode {
  id: string;
  parentId: string | null;
  question: string;
  depth: number;
  status: NodeStatus;
  sources: Source[];
  summary: string;
  children: TreeNode[];
}
