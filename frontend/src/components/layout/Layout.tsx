import React from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { useAuthStore } from "@/store/authStore";
import {
  NavigationBar,
  SearchInput,
  ToolbarButtonEmptyInverse,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  UserMenu,
} from "@planview/pv-toolbar";
import {
  Notification,
  Settings,
  Help,
  Support,
  Logout,
  LogoProjectplace,
} from "@planview/pv-icons";
import { Avatar, ListItem } from "@planview/pv-uikit";

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
  const navigate = useNavigate();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Wrapper>
      <NavigationBar aria-label="Main navigation" logo={<LogoProjectplace title="Planview Advisor" />}>
        <ToolbarSectionLeft>
          <ToolbarButtonEmptyInverse onClick={() => navigate("/")}>Overview</ToolbarButtonEmptyInverse>
          <ToolbarButtonEmptyInverse onClick={() => navigate("/documents")}>Documents</ToolbarButtonEmptyInverse>
        </ToolbarSectionLeft>
        <ToolbarSectionRight moreMenuLabel="More actions">
          <SearchInput />
          <ToolbarButtonEmptyInverse icon={<Notification />} tooltip="Notifications" />
          <UserMenu triggerElement={<Avatar aria-label="Design System avatar" initials="PC" />}>
            <ListItem icon={<Settings />} label="Settings" />
            <ListItem icon={<Help />} label="Help" />
            <ListItem icon={<Support />} label="Customer support" />
            <ListItem onActivate={handleLogout} icon={<Logout />} label="Log out" />
          </UserMenu>
        </ToolbarSectionRight>
      </NavigationBar>

      <Main>{children}</Main>
    </Wrapper>
  );
}
