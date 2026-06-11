import { useLocation, useNavigate } from "react-router-dom";
import styled from "styled-components";
import {
  NavigationBar,
  SearchInput,
  ToolbarButtonEmptyInverse,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  UserMenu,
} from "@planview/pv-toolbar";
import { Notification, Settings, Help, Support, Logout, LogoProjectplace, PlusCircleFilled } from "@planview/pv-icons";
import { Avatar, ListItem } from "@planview/pv-uikit";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";
import SearchPanel from "../documents/search/SearchPanel";
import AddSources from "../Sources";

const NavButton = styled(ToolbarButtonEmptyInverse)<{ $active?: boolean }>`
  border-bottom: 2px solid ${({ $active }) => ($active ? "rgba(255,255,255,0.9)" : "transparent")};
  border-radius: 0;
  font-weight: ${({ $active }) => ($active ? "700" : "400")};
  opacity: ${({ $active }) => ($active ? "1" : "0.8")};
`;

export default function AppNavigationBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuthStore();
  const [searchActive, setSearchActive] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [isDocumentOpen, setIsDocumentOpen] = useState(false)
  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path: string) => (path === "/" ? location.pathname === "/" : location.pathname.startsWith(path));

  return (
    <>
      <NavigationBar aria-label="Main navigation" logo={<LogoProjectplace title="Planview Advisor" />}>
        <ToolbarSectionLeft>
          <NavButton icon={<PlusCircleFilled />} onClick={() => {setIsDocumentOpen(true)}}>
            Add
          </NavButton>
          <NavButton $active={isActive("/")} onClick={() => navigate("/")}>
            Overview
          </NavButton>
          <NavButton
            $active={location.pathname.startsWith("/documents") || location.pathname.startsWith("/folders")}
            onClick={() => navigate("/documents")}
          >
            Documents
          </NavButton>
          <NavButton $active={isActive("/compliance")} onClick={() => navigate("/compliance")}>
            Compliance
          </NavButton>
          <NavButton $active={isActive("/sources")} onClick={() => navigate("/sources")}>
            Sources
          </NavButton>
        </ToolbarSectionLeft>
        <ToolbarSectionRight moreMenuLabel="More actions">
          <SearchInput
            onChange={(value) => setSearchText(value)}
            onFocus={() => {
              setSearchActive(true);
            }}
          />
          <ToolbarButtonEmptyInverse icon={<Notification />} tooltip="Notifications" />
          <UserMenu triggerElement={<Avatar aria-label="Design System avatar" initials="PC" />}>
            <ListItem icon={<Settings />} label="Settings" />
            <ListItem icon={<Help />} label="Help" />
            <ListItem icon={<Support />} label="Customer support" />
            <ListItem onActivate={handleLogout} icon={<Logout />} label="Log out" />
          </UserMenu>
        </ToolbarSectionRight>
      </NavigationBar>
      {searchActive ? (
        <SearchPanel
          query={searchText}
          onClose={() => {
            setSearchActive(false);
            setSearchText("");
          }}
        />
      ) : null}
      {isDocumentOpen && (
        <AddSources
          onClose={() => setIsDocumentOpen(false)}
        />
      )}
    </>
  );
}
