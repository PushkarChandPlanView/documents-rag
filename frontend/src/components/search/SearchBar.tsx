import { FormEvent, useState } from "react";
import styled from "styled-components";
import { borderRadius, color, shadow, spacing, text } from "@planview/pv-utilities";
import { searchApi } from "@/api/chat";
import type { DocumentSearchResult } from "@/types";

const SearchForm = styled.form`
  display: flex;
  gap: ${spacing.xsmall}px;
  margin-bottom: ${spacing.medium}px;
`;

const SearchInput = styled.input`
  flex: 1;
  padding: ${spacing.small}px ${spacing.medium}px;
  border: 1px solid ${color.borderLight};
  border-radius: 24px;
  ${text.regular};
  outline: none;
`;

const SearchButton = styled.button<{ $disabled: boolean }>`
  padding: ${spacing.small}px ${spacing.medium}px;
  background: ${color.backgroundPrimary};
  color: ${color.textInverse};
  border: none;
  border-radius: 24px;
  cursor: pointer;
  ${text.regularSemibold};
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
`;

const ErrorText = styled.p`
  color: ${color.textError};
`;

const NoResults = styled.p`
  color: ${color.textPlaceholder};
  text-align: center;
`;

const ResultsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
`;

const ResultCard = styled.div`
  background: ${color.backgroundNeutral0};
  ${borderRadius.medium()};
  padding: ${spacing.small}px;
  ${shadow.small};
  border-left: 4px solid ${color.backgroundPrimary};
`;

const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: ${spacing.xsmall}px;
`;

const ResultFilename = styled.span`
  ${text.regularSemibold};
  color: ${color.textPrimary};
`;

const ResultScore = styled.span`
  ${text.small};
  color: ${color.textSecondary};
`;

const ResultMeta = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  margin-bottom: ${spacing.xsmall}px;
`;

const ResultText = styled.p`
  margin: 0;
  ${text.regular};
  color: ${color.textSecondary};
  line-height: 1.6;
`;

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DocumentSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchApi.searchDocuments(query.trim());
      setResults(data.results || []);
      setSearched(true);
    } catch {
      setError("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !query.trim();

  return (
    <div>
      <SearchForm onSubmit={handleSearch}>
        <SearchInput
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search across all your documents..."
        />
        <SearchButton type="submit" disabled={isDisabled} $disabled={isDisabled}>
          {loading ? "Searching..." : "Search"}
        </SearchButton>
      </SearchForm>

      {error && <ErrorText>{error}</ErrorText>}

      {searched && results.length === 0 && (
        <NoResults>No results found for "{query}"</NoResults>
      )}

      <ResultsList>
        {results.map((result) => (
          <ResultCard key={result.document_id}>
            <ResultHeader>
              <ResultFilename>
                {result.document_name || `Document ${result.document_id.slice(0, 8)}`}
              </ResultFilename>
              <ResultScore>Score: {(result.score * 100).toFixed(1)}%</ResultScore>
            </ResultHeader>
            <ResultMeta>
              {result.file_type && <span>{result.file_type}</span>}
              {result.page_number != null && <span> · page {result.page_number}</span>}
              {result.file_size_bytes != null && (
                <span> · {(result.file_size_bytes / 1024).toFixed(0)} KB</span>
              )}
              <span> · {new Date(result.updated_at).toLocaleDateString()}</span>
              {result.status && <span> · {result.status}</span>}
            </ResultMeta>
            {result.description && (
              <ResultText style={{ color: color.textSecondary, marginBottom: `${spacing.xsmall}px` }}>
                {result.description}
              </ResultText>
            )}
            <ResultText>{result.snippet}</ResultText>
          </ResultCard>
        ))}
      </ResultsList>
    </div>
  );
}
