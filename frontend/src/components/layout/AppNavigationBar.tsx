import { useNavigate } from "react-router-dom";
import {
  NavigationBar,
  SearchInput,
  ToolbarButtonEmptyInverse,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  UserMenu,
} from "@planview/pv-toolbar";
import { Notification, Settings, Help, Support, Logout, LogoProjectplace } from "@planview/pv-icons";
import { Avatar, ListItem } from "@planview/pv-uikit";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";
import SearchPanel from "../documents/search/SearchPanel";

export default function AppNavigationBar() {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const [searchActive, setSearchActive] = useState(false);
  const [searchText, setSearchText] = useState("");
  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      <NavigationBar aria-label="Main navigation" logo={<LogoProjectplace title="Planview Advisor" />}>
        <ToolbarSectionLeft>
          <ToolbarButtonEmptyInverse onClick={() => navigate("/")}>Overview</ToolbarButtonEmptyInverse>
          <ToolbarButtonEmptyInverse onClick={() => navigate("/documents")}>Documents</ToolbarButtonEmptyInverse>
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
          onClose={() => { setSearchActive(false); setSearchText(""); }}
        />
      ) : null}
    </>
  );
}
