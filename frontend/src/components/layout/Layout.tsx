import { Link, useLocation, useNavigate } from "react-router-dom";
import styled from "styled-components";
import { useAuthStore } from "@/store/authStore";

const NAV_ITEMS = [
  { path: "/", label: "Dashboard" },
  { path: "/documents", label: "Documents" },
  { path: "/search", label: "Search" },
];

const Wrapper = styled.div`
  display: flex;
  width: 100%;
  height: 100%;
  font-family: system-ui, sans-serif;
  position: relative;
`;

const Sidebar = styled.nav`
  width: 220px;
  background: #1e1e2e;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 0;
`;

const SidebarHeader = styled.div`
  padding: 0 1.5rem 1.5rem;
  border-bottom: 1px solid #333;
  font-weight: 700;
  font-size: 1rem;
`;

const NavList = styled.div`
  flex: 1;
  padding: 1rem 0;
`;

const NavLink = styled(Link)<{ $active: boolean }>`
  display: block;
  padding: 0.625rem 1.5rem;
  color: inherit;
  text-decoration: none;
  font-size: 0.9rem;
  background: ${({ $active }) => ($active ? "#333" : "transparent")};
  border-left: 3px solid ${({ $active }) => ($active ? "#4f9cf9" : "transparent")};
`;

const SidebarFooter = styled.div`
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
  font-size: 0.8rem;
  color: #aaa;
`;

const UserEmail = styled.div`
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const LogoutButton = styled.button`
  background: none;
  border: 1px solid #555;
  color: #aaa;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
`;

const Main = styled.main`
  height: 100%;
  width: 100%;
  background: #f8f9fa;
`;

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { userEmail, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Wrapper>
      <Sidebar>
        <SidebarHeader>Document Intel</SidebarHeader>
        <NavList>
          {NAV_ITEMS.map(({ path, label }) => (
            <NavLink key={path} to={path} $active={location.pathname === path}>
              {label}
            </NavLink>
          ))}
        </NavList>
        <SidebarFooter>
          <UserEmail>{userEmail}</UserEmail>
          <LogoutButton onClick={handleLogout}>Sign Out</LogoutButton>
        </SidebarFooter>
      </Sidebar>

      <Main>
       {children}
      </Main>
    </Wrapper>
  );
}
