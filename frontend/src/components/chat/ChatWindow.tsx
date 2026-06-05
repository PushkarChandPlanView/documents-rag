import { FormEvent, useEffect, useRef, useState } from "react";
import styled from "styled-components";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamChat } from "@/api/chat";
import type { ChatMessage } from "@/types";

// ── Markdown elements ────────────────────────────────────────────────────────

const MdP = styled.p`margin: 0 0 0.5rem;`;
const MdUl = styled.ul`margin: 0 0 0.5rem; padding-left: 1.25rem;`;
const MdOl = styled.ol`margin: 0 0 0.5rem; padding-left: 1.25rem;`;
const MdLi = styled.li`margin-bottom: 0.2rem;`;
const MdH1 = styled.h1`font-size: 1.1rem; font-weight: 700; margin: 0.75rem 0 0.4rem;`;
const MdH2 = styled.h2`font-size: 1rem; font-weight: 700; margin: 0.75rem 0 0.4rem;`;
const MdH3 = styled.h3`font-size: 0.95rem; font-weight: 600; margin: 0.5rem 0 0.25rem;`;
const MdCode = styled.code`
  background: #f1f3f4;
  border-radius: 4px;
  padding: 0.1em 0.3em;
  font-size: 0.82rem;
  font-family: monospace;
`;
const MdBlockCode = styled(MdCode)`
  display: block;
  background: transparent;
  padding: 0;
`;
const MdPre = styled.pre`
  background: #f1f3f4;
  border-radius: 6px;
  padding: 0.75rem;
  overflow: auto;
  margin: 0 0 0.5rem;
`;
const MdBlockquote = styled.blockquote`
  border-left: 3px solid #ccc;
  padding-left: 0.75rem;
  color: #666;
  margin: 0 0 0.5rem;
`;

function normalizeMarkdown(text: string): string {
  return text
    .replace(/^[•●◦◆▪▸]\s+/gm, "- ")   // unicode bullets → markdown list
    .replace(/^(\s+)[•●◦◆▪▸]\s+/gm, "$1- "); // indented unicode bullets
}

function AssistantMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <MdP>{children}</MdP>,
        ul: ({ children }) => <MdUl>{children}</MdUl>,
        ol: ({ children }) => <MdOl>{children}</MdOl>,
        li: ({ children }) => <MdLi>{children}</MdLi>,
        h1: ({ children }) => <MdH1>{children}</MdH1>,
        h2: ({ children }) => <MdH2>{children}</MdH2>,
        h3: ({ children }) => <MdH3>{children}</MdH3>,
        code: ({ children, className }) => {
          const isBlock = !!className;
          return isBlock
            ? <MdBlockCode>{children}</MdBlockCode>
            : <MdCode>{children}</MdCode>;
        },
        pre: ({ children }) => <MdPre>{children}</MdPre>,
        blockquote: ({ children }) => <MdBlockquote>{children}</MdBlockquote>,
      }}
    >
      {normalizeMarkdown(content)}
    </ReactMarkdown>
  );
}

// ── Message ──────────────────────────────────────────────────────────────────

const MessageRow = styled.div<{ $isUser: boolean }>`
  display: flex;
  justify-content: ${({ $isUser }) => ($isUser ? "flex-end" : "flex-start")};
  margin-bottom: 1rem;
`;

const Bubble = styled.div<{ $isUser: boolean }>`
  max-width: 75%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: ${({ $isUser }) => ($isUser ? "#1a73e8" : "#fff")};
  color: ${({ $isUser }) => ($isUser ? "#fff" : "#333")};
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  font-size: 0.9rem;
  line-height: 1.6;
`;

const UserText = styled.p`margin: 0; white-space: pre-wrap;`;

const StatusText = styled.p`
  margin: 0;
  color: #888;
  font-size: 0.85rem;
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 6px;

  &::after {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #888;
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }
`;

const SourcesSection = styled.div`
  margin-top: 0.5rem;
  border-top: 1px solid #e0e0e0;
  padding-top: 0.5rem;
`;

const SourcesLabel = styled.p`margin: 0 0 0.25rem; font-size: 0.7rem; color: #666;`;

const SourceChip = styled.span`
  display: inline-block;
  margin: 2px;
  padding: 2px 6px;
  background: #f0f4ff;
  border-radius: 10px;
  font-size: 0.65rem;
  color: #1a73e8;
`;

function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <MessageRow $isUser={isUser}>
      <Bubble $isUser={isUser}>
        {isUser
          ? <UserText>{msg.content}</UserText>
          : msg.status && !msg.content
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
    </MessageRow>
  );
}

// ── ChatWindow ───────────────────────────────────────────────────────────────

const WindowWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: calc(100vh - 4rem);
`;

const MessageList = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
`;

const EmptyHint = styled.p`
  text-align: center;
  color: #999;
  margin-top: 4rem;
`;

const StreamingIndicator = styled.div`
  text-align: center;
  color: #999;
  font-size: 0.8rem;
`;

const InputForm = styled.form`
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  background: #fff;
`;

const TextInput = styled.input`
  flex: 1;
  padding: 0.625rem 1rem;
  border: 1px solid #ccc;
  border-radius: 24px;
  font-size: 0.9rem;
  outline: none;
`;

const SendButton = styled.button<{ $disabled: boolean }>`
  padding: 0.625rem 1.25rem;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-weight: 600;
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
`;

interface ChatWindowProps {
  documentId?: string;
  documentName?: string;
}

export function ChatWindow({ documentId, documentName }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([]);
    setInput("");
    setStreaming(false);
  }, [documentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      sources: [],
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      for await (const event of streamChat(userMsg.content, documentId ? [documentId] : undefined)) {
        if (event.type === "status" && event.message) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { ...updated[updated.length - 1], status: event.message };
            return updated;
          });
        } else if (event.token) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              status: undefined,
              content: updated[updated.length - 1].content + event.token,
            };
            return updated;
          });
        }
        if (event.done && event.sources && event.sources.length > 0) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              sources: event.sources,
            };
            return updated;
          });
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: "Sorry, an error occurred. Please try again.",
        };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  };

  const isDisabled = !input.trim() || streaming;

  return (
    <WindowWrapper>
      <MessageList>
        {messages.length === 0 && (
          <EmptyHint>
            {documentName
              ? `Ask a question about "${documentName}"...`
              : "Ask a question about your documents..."}
          </EmptyHint>
        )}
        {messages.map((msg) => <Message key={msg.id} msg={msg} />)}
        {streaming && <StreamingIndicator>Generating response...</StreamingIndicator>}
        <div ref={bottomRef} />
      </MessageList>
      <InputForm onSubmit={handleSubmit}>
        <TextInput
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents..."
          disabled={streaming}
        />
        <SendButton type="submit" disabled={isDisabled} $disabled={isDisabled}>
          Send
        </SendButton>
      </InputForm>
    </WindowWrapper>
  );
}
