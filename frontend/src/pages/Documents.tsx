import { useState } from "react";
import styled from "styled-components";
import Layout from "@/components/layout/Layout";
import { DocumentUpload } from "@/components/documents/DocumentUpload";
import { DocumentList } from "@/components/documents/DocumentList";
import { DocumentChatPanel } from "@/components/documents/DocumentChatPanel";
import type { Document } from "@/types";


const ContentArea = styled.div`
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
`;

const LeftPane = styled.div<{ $hasSelection: boolean }>`
  flex: ${({ $hasSelection }) => ($hasSelection ? "0 0 65%" : "1")};
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
  transition: flex 0.2s ease;
  overflow-y: ${({ $hasSelection }) => ($hasSelection ? "auto" : "visible")};
`;

const PageTitle = styled.h1`
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
`;

const SectionTitle = styled.h2`
  font-size: 1rem;
  font-weight: 600;
  margin-top: 0;
  margin-bottom: 1rem;
  color: #555;
`;

const RightPane = styled.div`
  flex: 0 0 35%;
  min-width: 0;
  min-height: 0;
`;

export default function Documents() {
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  const handleSelect = (doc: Document) => {
    setSelectedDoc((prev) => (prev?.id === doc.id ? null : doc));
  };

  const handleClose = () => setSelectedDoc(null);

  return (
    <Layout>
      <ContentArea>
        {/* Left pane — document list */}
        <LeftPane $hasSelection={!!selectedDoc}>
          <PageTitle>Documents</PageTitle>

          {!selectedDoc && (
            <div>
              <SectionTitle>Upload Document</SectionTitle>
              <DocumentUpload />
            </div>
          )}

          <div>
            <SectionTitle>Your Documents</SectionTitle>
            <DocumentList onSelect={handleSelect} selectedId={selectedDoc?.id} />
          </div>
        </LeftPane>

        {/* Right pane — chat panel */}
        {selectedDoc && (
          <RightPane>
            <DocumentChatPanel doc={selectedDoc} onClose={handleClose} />
          </RightPane>
        )}
      </ContentArea>
    </Layout>
  );
}
