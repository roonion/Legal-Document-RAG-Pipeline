"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import {
  MessageSquareText,
  FileText,
  BarChart3,
  Upload,
  ArrowRight,
  Sparkles,
  Shield,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useDocuments } from "@/hooks/use-documents";

const quickActions = [
  {
    href: "/dashboard/chat",
    icon: MessageSquareText,
    label: "Ask a Question",
    description: "Chat with your legal documents using AI",
    color: "bg-info/10 text-info",
  },
  {
    href: "/dashboard/documents",
    icon: Upload,
    label: "Upload Document",
    description: "Add PDFs to your knowledge base",
    color: "bg-success/10 text-success",
  },
  {
    href: "/dashboard/evaluation",
    icon: BarChart3,
    label: "View Metrics",
    description: "Check retrieval accuracy and quality",
    color: "bg-accent/10 text-accent",
  },
];

const features = [
  {
    icon: Sparkles,
    title: "AI-Powered Analysis",
    description: "Ask natural language questions and get precise answers with source citations.",
  },
  {
    icon: Shield,
    title: "Grounded in Evidence",
    description: "Every answer traces back to specific passages in your uploaded documents.",
  },
  {
    icon: Zap,
    title: "Intelligent Retrieval",
    description: "Hybrid search combines semantic understanding with keyword matching.",
  },
];

export default function DashboardPage() {
  const { data: docs } = useDocuments();
  const totalDocs = docs?.length ?? 0;
  const completedDocs = docs?.filter((d) => d.status === "completed").length ?? 0;
  const processingDocs = docs?.filter(
    (d) => !["completed", "failed"].includes(d.status),
  ).length ?? 0;

  return (
    <>
      <Header title="Overview" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-8">
          {/* Welcome */}
          <div className="animate-fade-in">
            <h2 className="text-2xl font-semibold text-foreground">
              Welcome to Legal RAG
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Your AI-powered legal document assistant. Upload contracts, ask questions, get cited answers.
            </p>
          </div>

          {/* Stats row */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="animate-fade-in">
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-info/10">
                  <FileText className="h-5 w-5 text-info" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{totalDocs}</p>
                  <p className="text-xs text-muted-foreground">Total Documents</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in" style={{ animationDelay: "50ms" }}>
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-success/10">
                  <Shield className="h-5 w-5 text-success" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{completedDocs}</p>
                  <p className="text-xs text-muted-foreground">Ready for Chat</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in" style={{ animationDelay: "100ms" }}>
              <CardContent className="flex items-center gap-4 p-5">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-warning/10">
                  <Zap className="h-5 w-5 text-warning" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{processingDocs}</p>
                  <p className="text-xs text-muted-foreground">Processing</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick actions */}
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Quick Actions
            </h3>
            <div className="grid gap-4 sm:grid-cols-3">
              {quickActions.map((action, i) => (
                <Link key={action.href} href={action.href}>
                  <Card
                    className="group cursor-pointer animate-fade-in"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <CardContent className="flex flex-col gap-3 p-5">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${action.color}`}>
                        <action.icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-foreground">
                            {action.label}
                          </p>
                          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {action.description}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </div>

          {/* Features */}
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wider">
              How It Works
            </h3>
            <div className="grid gap-4 sm:grid-cols-3">
              {features.map((f, i) => (
                <div
                  key={f.title}
                  className="animate-fade-in rounded-xl border border-border bg-card/50 p-5"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <f.icon className="h-5 w-5 text-accent" />
                  <h4 className="mt-3 text-sm font-semibold text-foreground">{f.title}</h4>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {f.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
