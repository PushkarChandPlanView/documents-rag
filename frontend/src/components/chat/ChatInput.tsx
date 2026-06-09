import { FormEvent } from "react";
import styled from "styled-components";
import { border, color } from "@planview/pv-utilities";
import { ButtonEmpty, Textarea } from "@planview/pv-uikit";
import { Request } from "@planview/pv-icons";

const ChatInputContainer = styled.div`
  display: flex;
  flex-direction: column;
  background-color: ${color.backgroundNeutral0};
  ${border.light}
`;
const SendSection = styled.div`
  display: flex;
  justify-content: flex-end;
  background-color: ${color.gray50};
`;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  streaming: boolean;
}

export function ChatInput({ value, onChange, onSubmit, streaming }: ChatInputProps) {
  const sendDisabled = !value.trim() || streaming;
  onSubmit;
  return (
    <ChatInputContainer>
      <Textarea
        value={value}
        onChange={(value) => onChange(value)}
        placeholder="Ask a question about your documents..."
        disabled={streaming}
      />
      <SendSection>
        <ButtonEmpty icon={<Request color="anvi" />} type="submit" disabled={sendDisabled} onClick={onSubmit}>
          send
        </ButtonEmpty>
      </SendSection>
    </ChatInputContainer>
  );
}
