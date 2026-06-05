import { useEffect, useState } from "react";
import { Textarea } from "@planview/pv-uikit";
import { useUpdateDescription } from "@/hooks/useDocuments";

interface DescriptionEditorProps {
  itemId: string;
  itemType: "document" | "folder";
  value: string | null;
}

export function DescriptionEditor({ itemId, itemType, value }: DescriptionEditorProps) {
  const [draft, setDraft] = useState(value ?? "");
  const { mutate: saveDescription } = useUpdateDescription();

  // sync draft when item changes
  useEffect(() => {
    setDraft(value ?? "");
  }, [itemId, value]);

  const handleBlur = () => {
    const trimmed = draft.trim();
    const next = trimmed || null;
    if (next !== value) {
      saveDescription({ id: itemId, type: itemType, description: next });
    }
  };

  return (
    <Textarea
      value={draft}
      onChange={(val) => setDraft(val)}
      onBlur={handleBlur}
      placeholder="Add a description…"
    />
  );
}
