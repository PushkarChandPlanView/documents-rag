import { useState } from "react";
import styled from "styled-components";
import { Input, Modal, MODAL_MEDIUM } from "@planview/pv-uikit";
import { useAddLink } from "@/hooks/useDocuments";

const ErrorText = styled.p`
  color: #c62828;
  font-size: 0.75rem;
  margin: 4px 0 0;
`;

const FieldLabel = styled.label`
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 4px;
`;

const FieldGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

interface AddLinkDialogProps {
  open: boolean;
  folderId?: string;
  onClose: () => void;
}

export function AddLinkDialog({ open, folderId, onClose }: AddLinkDialogProps) {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [urlError, setUrlError] = useState<string | undefined>(undefined);
  const { mutate: addLink } = useAddLink();

  if (!open) return null;

  const handleConfirm = () => {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setUrlError("URL is required");
      return;
    }
    try {
      new URL(trimmedUrl);
    } catch {
      setUrlError("Please enter a valid URL (e.g. https://example.com)");
      return;
    }

    addLink(
      { url: trimmedUrl, title: title.trim() || undefined, folderId },
      {
        onSuccess: () => {
          setUrl("");
          setTitle("");
          setUrlError(undefined);
          onClose();
        },
        onError: () => setUrlError("Failed to add link. Please try again."),
      },
    );
  };

  const handleCancel = () => {
    setUrl("");
    setTitle("");
    setUrlError(undefined);
    onClose();
  };

  return (
    <Modal
      headerText="Add Link"
      confirmText="Add"
      cancelText="Cancel"
      onConfirm={handleConfirm}
      onCancel={handleCancel}
      size={MODAL_MEDIUM}
    >
      <FieldGroup>
        <div>
          <FieldLabel htmlFor="link-url-input">URL</FieldLabel>
          <Input
            id="link-url-input"
            value={url}
            onChange={(v) => {
              setUrl(v);
              if (urlError) setUrlError(undefined);
            }}
            error={!!urlError}
            autoFocus
          />
          {urlError && <ErrorText>{urlError}</ErrorText>}
        </div>
        <div>
          <FieldLabel htmlFor="link-title-input">Title (optional)</FieldLabel>
          <Input
            id="link-title-input"
            value={title}
            onChange={setTitle}
          />
        </div>
      </FieldGroup>
    </Modal>
  );
}
