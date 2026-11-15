import { create } from "zustand";

interface DocumentState {
  selectedDocumentId: string | null;
  setSelectedDocumentId: (id: string | null) => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  selectedDocumentId: null,
  setSelectedDocumentId: (id) => set({ selectedDocumentId: id }),
}));
