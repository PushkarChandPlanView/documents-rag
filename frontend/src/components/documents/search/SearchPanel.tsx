import { useEffect, useRef, useState } from "react";
import { Portal } from "@planview/pv-uikit";
import styled, { ThemeProvider } from "styled-components";
import zindex from "@planview/pv-utilities/lib/zindex";
import { borderRadius, color, shadow, size, spacing, text } from "@planview/pv-utilities";
import { searchApi } from "@/api/chat";
import type { DocumentSearchResult } from "@/types";
import LandingPage from "./LandingPage";

declare module "styled-components" {
  export interface DefaultTheme {
    zindex: number;
  }
}

const MAX_META_POPOVER_HEIGHT = 300;
const LIST_WIDTH = 400;
const FILTER_WIDTH = 280;

const Wrapper = styled.div`
  background-color: ${color.gray0};
  ${text.regular};
  box-sizing: border-box;
  z-index: ${({ theme }) => theme.zindex};
  position: absolute;
  width: ${LIST_WIDTH + FILTER_WIDTH}px;
  transition: width 0.3s, left 0.3s;
  min-height: 215px;
  top: ${size.medium - 1}px;
  right: 100px;
  height: calc(100vh - ${size.medium}px - ${MAX_META_POPOVER_HEIGHT}px - ${spacing.small}px);
  ${shadow.regular};
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const ResultsList = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.xsmall}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.xsmall}px;
`;

const ResultCard = styled.div`
  padding: ${spacing.small}px;
  ${borderRadius.medium()};
  background: ${color.backgroundNeutral0};
  border: 1px solid ${color.borderLight};
  cursor: pointer;

  &:hover {
    border-color: ${color.backgroundPrimary};
    background: ${color.primary0};
  }
`;

const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2px;
`;

const ResultName = styled.span`
  ${text.regular};
  font-weight: 600;
  color: ${color.textPrimary};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
`;

const ResultScore = styled.span`
  ${text.small};
  color: ${color.textSecondary};
  flex-shrink: 0;
`;

const ResultMeta = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  margin-bottom: ${spacing.xsmall}px;
`;

const ResultSnippet = styled.p`
  margin: 0;
  ${text.small};
  color: ${color.textSecondary};
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

const StateMessage = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  ${text.regular};
  color: ${color.textSecondary};
  padding: ${spacing.medium}px;
  text-align: center;
`;

const DEBOUNCE_MS = 350;
const MIN_QUERY_LENGTH = 2;

type SearchPanelProps = {
  query: string;
  onClose: () => void;
};

const SearchPanel = ({ query, onClose }: SearchPanelProps) => {
  const [results, setResults] = useState<DocumentSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [onClose]);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setResults([]);
      setLoading(false);
      setError(false);
      return;
    }

    setLoading(true);
    setError(false);

    timerRef.current = setTimeout(async () => {
      try {
        const data = await searchApi.searchDocuments(trimmed);
        setResults(data.results ?? []);
      } catch {
        setError(true);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  const renderBody = () => {
    if (loading) return <StateMessage>Searching…</StateMessage>;
    if (error) return <StateMessage>Search failed. Please try again.</StateMessage>;
    if (query.trim().length < MIN_QUERY_LENGTH) return <LandingPage />;
    if (results.length === 0) return <StateMessage>No documents matched "{query.trim()}"</StateMessage>;

    return results.map((r) => (
      <ResultCard key={r.document_id}>
        <ResultHeader>
          <ResultName title={r.document_name}>{r.document_name}</ResultName>
          <ResultScore>{(r.score * 100).toFixed(0)}% match</ResultScore>
        </ResultHeader>
        <ResultMeta>
          {r.file_type && <span>{r.file_type.toUpperCase()}</span>}
          {r.page_number != null && <span> · p.{r.page_number}</span>}
          {r.file_size_bytes != null && <span> · {(r.file_size_bytes / 1024).toFixed(0)} KB</span>}
        </ResultMeta>
        <ResultSnippet>{r.snippet}</ResultSnippet>
      </ResultCard>
    ));
  };

  return (
    <Portal>
      <ThemeProvider theme={zindex.ZindexTheme({ zindex: 0 })}>
        <Wrapper id="resultPaneVisible" ref={wrapperRef}>
          <ResultsList>{renderBody()}</ResultsList>
        </Wrapper>
      </ThemeProvider>
    </Portal>
  );
};

export default SearchPanel;
