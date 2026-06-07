import styled from "styled-components";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { borderRadius, color, spacing, text } from "@planview/pv-utilities";

const MdP = styled.p`margin: 0 0 ${spacing.xsmall}px;`;
const MdUl = styled.ul`margin: 0 0 ${spacing.xsmall}px; padding-left: ${spacing.medium}px;`;
const MdOl = styled.ol`margin: 0 0 ${spacing.xsmall}px; padding-left: ${spacing.medium}px;`;
const MdLi = styled.li`margin-bottom: 2px;`;
const MdH1 = styled.h1`${text.regular}; margin: ${spacing.small}px 0 ${spacing.xsmall}px;`;
const MdH2 = styled.h2`${text.h2}; margin: ${spacing.small}px 0 ${spacing.xsmall}px;`;
const MdH3 = styled.h3`${text.regularSemibold}; margin: ${spacing.xsmall}px 0 2px;`;
const MdCode = styled.code`
  background: ${color.backgroundNeutral50};
  ${borderRadius.small()};
  padding: 0.1em 0.3em;
  font-size: 0.82rem;
`;
const MdBlockCode = styled(MdCode)`
  display: block;
  background: transparent;
  padding: 0;
`;
const MdPre = styled.pre`
  background: ${color.backgroundNeutral50};
  ${borderRadius.medium()};
  padding: ${spacing.small}px;
  overflow: auto;
  margin: 0 0 ${spacing.xsmall}px;
`;
const MdBlockquote = styled.blockquote`
  border-left: 3px solid ${color.borderLight};
  padding-left: ${spacing.small}px;
  color: ${color.textSecondary};
  margin: 0 0 ${spacing.xsmall}px;
`;

function normalizeMarkdown(text: string): string {
  return text
    .replace(/^[•●◦◆▪▸]\s+/gm, "- ")
    .replace(/^(\s+)[•●◦◆▪▸]\s+/gm, "$1- ");
}

export function AssistantMarkdown({ content }: { content: string }) {
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
