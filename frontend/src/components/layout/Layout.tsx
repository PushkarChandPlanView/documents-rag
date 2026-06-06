import React from "react";
import styled from "styled-components";
import AppNavigationBar from "./AppNavigationBar";

const Wrapper = styled.div`
  display: flex;
  width: 100%;
  height: 100%;
  font-family: system-ui, sans-serif;
  position: relative;
  flex-direction: column;
`;

const Main = styled.main`
  height: 100%;
  width: 100%;
  background: #f8f9fa;
  box-sizing: border-box;
`;

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Wrapper>
      <AppNavigationBar />
      <Main>{children}</Main>
    </Wrapper>
  );
}
