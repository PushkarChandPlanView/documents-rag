import { useRef } from "react";
import { Modal, MODAL_MEDIUM } from "@planview/pv-uikit";
import { FileUpload } from "./FileUpload";
import { documentsApi } from "@/api/documents";
import { queryClient } from "@/store/queryClient";

interface FileUploadDialogProps {
  open: boolean;
  onClose: () => void;
  folderId?: string;
}

export function FileUploadDialog({ open, onClose, folderId }: FileUploadDialogProps) {
  const uploadedDocIds = useRef<Set<string>>(new Set());

  if (!open) return null;

  const handleConfirm = () => {
    uploadedDocIds.current.clear();
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    onClose();
  };

  const handleCancel = async () => {
    await Promise.all(
      [...uploadedDocIds.current].map((id) => documentsApi.delete(id).catch(() => {}))
    );
    uploadedDocIds.current.clear();
    onClose();
  };

  return (
    <Modal
      headerText="Upload Files"
      confirmText="OK"
      cancelText="Cancel"
      onConfirm={handleConfirm}
      onCancel={handleCancel}
      size={MODAL_MEDIUM}
    >
      <FileUpload
        onUploaded={(docId) => { uploadedDocIds.current.add(docId); }}
        onRemoved={(docId) => { uploadedDocIds.current.delete(docId); }}
        folderId={folderId}
      />
    </Modal>
  );
}
