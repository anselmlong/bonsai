import { ResearchTree } from "@/components/ResearchTree";

export default async function ResearchPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <ResearchTree jobId={jobId} />;
}
