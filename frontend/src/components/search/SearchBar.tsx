import { FormEvent, useState } from "react";
import styled from "styled-components";
import { searchApi } from "@/api/chat";
import type { DocumentSearchResult } from "@/types";

const SearchForm = styled.form`
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
`;

const SearchInput = styled.input`
  flex: 1;
  padding: 0.625rem 1rem;
  border: 1px solid #ccc;
  border-radius: 24px;
  font-size: 0.9rem;
  outline: none;
`;

const SearchButton = styled.button<{ $disabled: boolean }>`
  padding: 0.625rem 1.25rem;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-weight: 600;
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
`;

const ErrorText = styled.p`
  color: #d32f2f;
`;

const NoResults = styled.p`
  color: #999;
  text-align: center;
`;

const ResultsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const ResultCard = styled.div`
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  border-left: 4px solid #1a73e8;
`;

const ResultHeader = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
`;

const ResultFilename = styled.span`
  font-weight: 600;
  font-size: 0.875rem;
  color: #333;
`;

const ResultScore = styled.span`
  font-size: 0.75rem;
  color: #888;
`;

const ResultMeta = styled.div`
  font-size: 0.75rem;
  color: #888;
  margin-bottom: 0.5rem;
`;

const ResultText = styled.p`
  margin: 0;
  font-size: 0.875rem;
  color: #555;
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
              <ResultText style={{ color: "#666", marginBottom: "0.4rem" }}>
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
