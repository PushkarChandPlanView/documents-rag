import styled from "styled-components";
import { color } from "@planview/pv-utilities";
import AppNavigationBar from "./AppNavigationBar";
import { Outlet } from "react-router-dom";

const Wrapper = styled.div`
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
  flex-direction: column;
`;

const Main = styled.main`
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  background: ${color.backgroundNeutral50};
  box-sizing: border-box;
`;

export default function Layout() {
  return (
    <Wrapper>
      <AppNavigationBar />
      <Main>
        <Outlet />
      </Main>
    </Wrapper>
  );
}
