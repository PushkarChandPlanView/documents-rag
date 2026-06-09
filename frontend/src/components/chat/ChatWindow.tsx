import { FormEvent, useEffect, useRef, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { streamChat } from "@/api/chat";
import { documentsApi } from "@/api/documents";
import { editsApi } from "@/api/edits";
import type { ChatMessage } from "@/types";
import { Message } from "./Message";
import { ChatInput } from "./ChatInput";

const WindowWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: calc(100vh - 10rem);
`;

const MessageList = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.small}px;
`;

const EmptyHint = styled.p`
  text-align: center;
  color: ${color.textPlaceholder};
  margin-top: ${spacing.large}px;
`;

const StreamingIndicator = styled.div`
  text-align: center;
  color: ${color.textPlaceholder};
  ${text.small};
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

    if (!documentId) return;

    documentsApi.get(documentId).then((doc) => {
      if (doc.summary) {
        setMessages([
          {
            id: crypto.randomUUID(),
            role: "summary",
            content: `\n\n${doc.summary}`,
            timestamp: new Date(),
          },
        ]);
      }
    }).catch(() => {
      // silently ignore — chat still works without a summary
    });
  }, [documentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const EDIT_INTENT_RE = /\b(update|add|remove|rewrite|change|modify|edit|fix|delete|replace|insert|correct)\b/i;

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

    // ── Edit intent: call the edit API instead of the chat stream ────────────
    if (documentId && EDIT_INTENT_RE.test(userMsg.content)) {
      const pendingMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "edit_proposal",
        content: userMsg.content,
        status: "Analyzing your request and generating a preview…",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, pendingMsg]);
      try {
        const proposal = await editsApi.propose(documentId, userMsg.content);
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            status: undefined,
            editProposal: {
              edit_id: proposal.id,
              document_id: proposal.document_id,
              original_content: proposal.original_content,
              proposed_content: proposal.proposed_content,
              status: proposal.status,
            },
          };
          return updated;
        });
      } catch {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            role: "assistant",
            status: undefined,
            content: "Sorry, could not generate an edit preview. Please try again.",
          };
          return updated;
        });
      } finally {
        setStreaming(false);
      }
      return;
    }
    // ── Normal chat stream ───────────────────────────────────────────────────

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      sources: [],
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      // Accumulate thinking/answer in plain variables — no React batching issues.
      // qwen3 emits thinking content (no opening <think> tag) then </think> then answer.
      let thinkingBuf = "";
      let thinkingDone = false;

      for await (const event of streamChat(userMsg.content, documentId ? [documentId] : undefined)) {
        if (event.type === "status" && event.message) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { ...updated[updated.length - 1], status: event.message };
            return updated;
          });
        } else if (event.token) {
          const token = event.token;

          if (!thinkingDone) {
            thinkingBuf += token;
            const splitIdx = thinkingBuf.indexOf("</think>");

            if (splitIdx !== -1) {
              // Found </think>: move buffer to thinking, reset content to answer
              thinkingDone = true;
              const thinkingText = thinkingBuf.slice(0, splitIdx);
              const answerText = thinkingBuf.slice(splitIdx + 8).replace(/^\n+/, "");
              thinkingBuf = "";

              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  status: undefined,
                  thinking: thinkingText || undefined,
                  thinkingComplete: true,
                  content: answerText,
                };
                return updated;
              });
            } else {
              // No </think> yet — stream directly into content so the user sees output
              const snapshot = thinkingBuf;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  status: undefined,
                  content: snapshot,
                };
                return updated;
              });
            }
          } else {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + token,
              };
              return updated;
            });
          }
        }
        if (event.done) {
          if (event.sources && event.sources.length > 0) {
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

  return (
    <WindowWrapper>
      <MessageList>
        {messages.length === 0 && (
          <EmptyHint>
            {documentName
              ? `Loading summary for "${documentName}"...`
              : "Ask a question about your documents..."}
          </EmptyHint>
        )}
        {messages.map((msg) => <Message key={msg.id} msg={msg} />)}
        {streaming && <StreamingIndicator>Generating response...</StreamingIndicator>}
        <div ref={bottomRef} />
      </MessageList>
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        streaming={streaming}
      />
    </WindowWrapper>
  );
}
