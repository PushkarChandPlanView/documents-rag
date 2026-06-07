import { FormEvent } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";

const InputForm = styled.form`
  display: flex;
  gap: ${spacing.xsmall}px;
  padding: ${spacing.small}px;
  border-top: 1px solid ${color.borderLight};
  background: ${color.backgroundNeutral0};
`;

const TextInput = styled.input`
  flex: 1;
  padding: ${spacing.small}px ${spacing.medium}px;
  border: 1px solid ${color.borderLight};
  border-radius: 24px;
  ${text.regular};
  outline: none;
`;

const SendButton = styled.button<{ $disabled: boolean }>`
  padding: ${spacing.small}px ${spacing.medium}px;
  background: ${color.backgroundPrimary};
  color: ${color.textInverse};
  border: none;
  border-radius: 24px;
  cursor: pointer;
  ${text.regularSemibold};
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
`;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  streaming: boolean;
}

export function ChatInput({ value, onChange, onSubmit, streaming }: ChatInputProps) {
  const sendDisabled = !value.trim() || streaming;
  return (
    <InputForm onSubmit={onSubmit}>
      <TextInput
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ask a question about your documents..."
        disabled={streaming}
      />
      <SendButton type="submit" disabled={sendDisabled} $disabled={sendDisabled}>
        Send
      </SendButton>
    </InputForm>
  );
}
