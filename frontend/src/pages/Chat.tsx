import styled from "styled-components";
import Layout from "@/components/layout/Layout";
import { ChatWindow } from "@/components/chat/ChatWindow";

const PageTitle = styled.h1`
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.5rem;
  font-weight: 700;
`;

export default function Chat() {
  return (
    <Layout>
      <PageTitle>Document Q&A</PageTitle>
      <ChatWindow />
    </Layout>
  );
}
