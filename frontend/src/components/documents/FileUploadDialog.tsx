import { Modal, MODAL_MEDIUM } from "@planview/pv-uikit";
import { FileUpload } from "./FileUpload";

interface FileUploadDialogProps {
  open: boolean;
  onClose: () => void;
  folderId?: string;
}

export function FileUploadDialog({ open, onClose, folderId }: FileUploadDialogProps) {
  if (!open) return null;

  return (
    <Modal
      headerText="Upload Files"
      confirmText="OK"
      onConfirm={onClose}
      onCancel={onClose}
      size={MODAL_MEDIUM}
    >
      <FileUpload onDone={onClose} folderId={folderId} />
    </Modal>
  );
}
