import { useState } from "react";
import styled from "styled-components";
import { Input, Modal, MODAL_SMALL } from "@planview/pv-uikit";
import { useCreateFolder } from "@/hooks/useFolders";

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

interface CreateFolderDialogProps {
  open: boolean;
  parentId?: string;
  onClose: () => void;
}

export function CreateFolderDialog({ open, parentId, onClose }: CreateFolderDialogProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const { mutate: createFolder } = useCreateFolder();

  if (!open) return null;

  const handleConfirm = () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Folder name is required");
      return;
    }
    createFolder(
      { name: trimmed, parentId },
      {
        onSuccess: () => {
          setName("");
          setError(undefined);
          onClose();
        },
        onError: () => setError("Failed to create folder. Please try again."),
      },
    );
  };

  const handleCancel = () => {
    setName("");
    setError(undefined);
    onClose();
  };

  return (
    <Modal
      headerText="New Folder"
      confirmText="Create"
      cancelText="Cancel"
      onConfirm={handleConfirm}
      onCancel={handleCancel}
      size={MODAL_SMALL}
    >
      <div>
        <FieldLabel htmlFor="folder-name-input">Folder name</FieldLabel>
        <Input
          id="folder-name-input"
          value={name}
          onChange={(v) => {
            setName(v);
            if (error) setError(undefined);
          }}
          error={!!error}
          autoFocus
        />
        {error && <ErrorText>{error}</ErrorText>}
      </div>
    </Modal>
  );
}
