import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const PageWrapper = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
`;

const Card = styled.div`
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.1);
  width: 360px;
`;

const Title = styled.h1`
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  font-weight: 600;
`;

const TabRow = styled.div`
  display: flex;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e0e0e0;
`;

const TabButton = styled.button<{ $active: boolean }>`
  flex: 1;
  padding: 0.5rem;
  border: none;
  background: none;
  border-bottom: ${({ $active }) => ($active ? "2px solid #1a73e8" : "none")};
  color: ${({ $active }) => ($active ? "#1a73e8" : "#666")};
  cursor: pointer;
  font-weight: ${({ $active }) => ($active ? 600 : 400)};
  margin-bottom: -2px;
`;

const FieldGroup = styled.div<{ $mb?: string }>`
  margin-bottom: ${({ $mb }) => $mb ?? "1rem"};
`;

const Label = styled.label`
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  color: #444;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
`;

const ErrorText = styled.p`
  color: #d32f2f;
  margin-bottom: 1rem;
  font-size: 0.875rem;
`;

const SubmitButton = styled.button<{ $loading: boolean }>`
  width: 100%;
  padding: 0.75rem;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: ${({ $loading }) => ($loading ? "not-allowed" : "pointer")};
  opacity: ${({ $loading }) => ($loading ? 0.7 : 1)};
`;

export default function Login() {
  const navigate = useNavigate();
  const setTokens = useAuthStore((s) => s.setTokens);
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
        await authApi.register(email, password);
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
          <FieldGroup>
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </FieldGroup>
          <FieldGroup $mb="1.5rem">
            <Label>Password</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </FieldGroup>
          {error && <ErrorText>{error}</ErrorText>}
          <SubmitButton type="submit" disabled={loading} $loading={loading}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </SubmitButton>
        </form>
      </Card>
    </PageWrapper>
  );
}
