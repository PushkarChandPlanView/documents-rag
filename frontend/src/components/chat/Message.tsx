import styled from "styled-components";
import type { ChatMessage } from "@/types";
import { borderRadius, color, shadow, spacing, text } from "@planview/pv-utilities";
import { AssistantMarkdown } from "./AssistantMarkdown";

const MessageRow = styled.div<{ $isUser: boolean }>`
  display: flex;
  justify-content: ${({ $isUser }) => ($isUser ? "flex-end" : "flex-start")};
  margin-bottom: ${spacing.small}px;
`;

const Bubble = styled.div<{ $isUser: boolean }>`
  max-width: 75%;
  padding: ${spacing.small}px ${spacing.medium}px;
  border-radius: 12px;
  background: ${({ $isUser }) => ($isUser ? color.backgroundPrimary : color.backgroundNeutral0)};
  color: ${({ $isUser }) => ($isUser ? color.textInverse : color.textPrimary)};
  ${shadow.small};
  ${text.regular};
  line-height: 1.6;
`;

const UserText = styled.p`margin: 0; white-space: pre-wrap;`;

const StatusText = styled.p`
  margin: 0;
  ${text.regularItalic};
  color: ${color.textSecondary};
  display: flex;
  align-items: center;
  gap: ${spacing.xsmall}px;

  &::after {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: ${color.textSecondary};
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
`;

const SourcesSection = styled.div`
  margin-top: ${spacing.xsmall}px;
  border-top: 1px solid ${color.borderLight};
  padding-top: ${spacing.xsmall}px;
`;

const SourcesLabel = styled.p`
  margin: 0 0 ${spacing.xsmall}px;
  ${text.small};
  color: ${color.textSecondary};
`;

const SourceChip = styled.span`
  display: inline-block;
  margin: 2px;
  padding: 2px ${spacing.xsmall}px;
  background: ${color.primary0};
  border-radius: 10px;
  ${text.small};
  color: ${color.backgroundPrimary};
`;

const AssistantColumn = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  gap: ${spacing.xsmall}px;
`;

const ThinkingBlock = styled.details`
  width: 90%;
  border: 1px solid ${color.borderLight};
  ${borderRadius.medium()};
  overflow: hidden;
  background: ${color.backgroundNeutral50};
`;

const ThinkingSummary = styled.summary`
  padding: ${spacing.xsmall}px ${spacing.small}px;
  ${text.small};
  color: ${color.textSecondary};
  cursor: pointer;
  user-select: none;
  list-style: none;
  display: flex;
  align-items: center;
  gap: ${spacing.xsmall}px;

  &::before {
    content: "▶";
    font-size: 0.6rem;
    transition: transform 0.15s;
  }

  details[open] > &::before {
    transform: rotate(90deg);
  }
`;

const ThinkingContent = styled.div`
  padding: ${spacing.xsmall}px ${spacing.small}px;
  ${text.small};
  color: ${color.textSecondary};
  border-top: 1px solid ${color.borderLight};
  white-space: pre-wrap;
  max-height: 220px;
  overflow-y: auto;
`;

export function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <MessageRow $isUser={isUser}>
      {isUser ? (
        <Bubble $isUser>
          <UserText>{msg.content}</UserText>
        </Bubble>
      ) : (
        <AssistantColumn>
          {msg.thinking && (
            <ThinkingBlock>
              <ThinkingSummary>Thinking…</ThinkingSummary>
              <ThinkingContent>{msg.thinking}</ThinkingContent>
            </ThinkingBlock>
          )}
          <Bubble $isUser={false}>
            {msg.status && !msg.content
              ? <StatusText>{msg.status}</StatusText>
              : <AssistantMarkdown content={msg.content} />
            }
            {msg.sources && msg.sources.length > 0 && (
              <SourcesSection>
                <SourcesLabel>Sources:</SourcesLabel>
                {msg.sources.map((s, i) => (
                  <SourceChip key={i}>
                    doc:{s.document_id.slice(0, 8)}{s.page_number ? ` p.${s.page_number}` : ""}
                  </SourceChip>
                ))}
              </SourcesSection>
            )}
          </Bubble>
        </AssistantColumn>
      )}
    </MessageRow>
  );
}
