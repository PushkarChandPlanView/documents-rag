import styled from "styled-components";
import Layout from "@/components/layout/Layout";
import { SearchBar } from "@/components/search/SearchBar";

const PageTitle = styled.h1`
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  font-weight: 700;
`;

export default function Search() {
  return (
    <Layout>
      <PageTitle>Semantic Search</PageTitle>
      <SearchBar />
    </Layout>
  );
}
