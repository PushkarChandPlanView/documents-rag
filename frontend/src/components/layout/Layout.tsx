import React from "react";
import styled from "styled-components";
import { color } from "@planview/pv-utilities";
import AppNavigationBar from "./AppNavigationBar";

const Wrapper = styled.div`
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
  flex-direction: column;
`;

const Main = styled.main`
  height: 100%;
  width: 100%;
  background: ${color.backgroundNeutral50};
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
