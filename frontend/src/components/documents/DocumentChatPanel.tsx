import styled from "styled-components";
import { ChatWindow } from "@/components/chat/ChatWindow";
import type { Document } from "@/types";

const Panel = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  overflow: hidden;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e0e0e0;
  background: #f8f9fa;
  flex-shrink: 0;
`;

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
`;

const ChatBadge = styled.span`
  background: #e8f0fe;
  color: #1a73e8;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
`;

const DocName = styled.span`
  font-weight: 600;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #333;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  cursor: pointer;
  color: #666;
  font-size: 1.2rem;
  line-height: 1;
  padding: 0 0.25rem;
  flex-shrink: 0;
`;

const ChatArea = styled.div`
  flex: 1;
  overflow: hidden;
`;

interface DocumentChatPanelProps {
  doc: Document;
  onClose: () => void;
}

export function DocumentChatPanel({ doc, onClose }: DocumentChatPanelProps) {
  return (
    <Panel>
      <Header>
        <HeaderLeft>
          <ChatBadge>Chat</ChatBadge>
          <DocName title={doc.filename}>{doc.filename}</DocName>
        </HeaderLeft>
        <CloseButton onClick={onClose} title="Close chat">✕</CloseButton>
      </Header>
      <ChatArea>
        <ChatWindow documentId={doc.id} documentName={doc.filename} />
      </ChatArea>
    </Panel>
  );
}
