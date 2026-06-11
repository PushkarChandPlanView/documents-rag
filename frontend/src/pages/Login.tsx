import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { borderRadius, color, shadow, spacing, text } from "@planview/pv-utilities";
import { Input } from "@planview/pv-form";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const PageWrapper = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${color.backgroundNeutral50};
`;

const Card = styled.div`
  background: ${color.backgroundNeutral0};
  padding: 2rem;
  ${borderRadius.medium()};
  ${shadow.regular};
  width: 360px;
`;

const Title = styled.h1`
  margin-bottom: ${spacing.medium}px;
  font-size: 1.5rem;
  font-weight: 600;
`;

const TabRow = styled.div`
  display: flex;
  margin-bottom: ${spacing.medium}px;
  border-bottom: 2px solid ${color.borderLight};
`;

const TabButton = styled.button<{ $active: boolean }>`
  flex: 1;
  padding: ${spacing.xsmall}px;
  border: none;
  background: none;
  border-bottom: ${({ $active }) => ($active ? `2px solid ${color.backgroundPrimary}` : "none")};
  color: ${({ $active }) => ($active ? color.backgroundPrimary : color.textSecondary)};
  cursor: pointer;
  font-weight: ${({ $active }) => ($active ? 600 : 400)};
  margin-bottom: -2px;
`;

const ErrorText = styled.p`
  color: ${color.textError};
  margin-bottom: ${spacing.small}px;
  ${text.regular};
`;

const SubmitButton = styled.button<{ $loading: boolean }>`
  width: 100%;
  padding: ${spacing.small}px;
  background: ${color.backgroundPrimary};
  color: ${color.textInverse};
  border: none;
  ${borderRadius.small()};
  ${text.regular};
  cursor: ${({ $loading }) => ($loading ? "not-allowed" : "pointer")};
  opacity: ${({ $loading }) => ($loading ? 0.7 : 1)};
`;

export default function Login() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await authApi.register(email, password, firstName, lastName);
      }
      const tokens = await authApi.login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token, email);
      navigate("/");
    } catch {
      setError(mode === "login" ? "Invalid email or password." : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <Card>
        <Title>Document Intelligence</Title>
        <TabRow>
          {(["login", "register"] as const).map((m) => (
            <TabButton key={m} $active={mode === m} onClick={() => setMode(m)}>
              {m === "login" ? "Sign In" : "Register"}
            </TabButton>
          ))}
        </TabRow>
        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <>
              <Input
                label="First Name"
                value={firstName}
                onChange={(value) => setFirstName(value)}
                placeholder="First name"
                withAsterisk
              />
              <Input
                label="Last Name"
                value={lastName}
                onChange={(value) => setLastName(value)}
                placeholder="Last name"
                withAsterisk
              />
            </>
          )}
          <Input label="Email"    type="email"    value={email}    onChange={(value) => setEmail(value)}    placeholder="you@example.com" withAsterisk />
          <Input label="Password" type="password" value={password} onChange={(value) => setPassword(value)} placeholder="••••••••" withAsterisk />
          {error && <ErrorText>{error}</ErrorText>}
          <SubmitButton type="submit" disabled={loading} $loading={loading}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </SubmitButton>
        </form>
      </Card>
    </PageWrapper>
  );
}
