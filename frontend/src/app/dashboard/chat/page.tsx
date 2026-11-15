"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { ChatPanel } from "@/components/chat/chat-panel";
import { PdfViewer } from "@/components/pdf/pdf-viewer";
import type { Citation } from "@/types/chat";

export default function ChatPage() {
  const [pdfUrl, setPdfUrl] = useState("");
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null,
  );

  const handleCitationsReceived = useCallback((citations: Citation[]) => {
    setActiveCitations(citations);
    const docId = citations.find((c) => c.document_id)?.document_id;
    if (docId) {
      setPdfUrl(`/api/pdf/${docId}`);
    }
  }, []);

  const handleCitationClick = useCallback(
    (citation: Citation) => {
      setSelectedCitation(citation);
      if (citation.document_id) {
        setPdfUrl(`/api/pdf/${citation.document_id}`);
      }
    },
    [],
  );

  return (
    <>
      <Header title="Chat & Sources" />
      <main className="grid flex-1 gap-4 overflow-hidden p-6 lg:grid-cols-2">
        <ChatPanel
          onCitationsReceived={handleCitationsReceived}
          onCitationClick={handleCitationClick}
        />
        <div className="hidden lg:block">
          <PdfViewer
            documentUrl={pdfUrl}
            highlights={activeCitations}
            selectedCitation={selectedCitation}
          />
        </div>
      </main>
    </>
  );
}
