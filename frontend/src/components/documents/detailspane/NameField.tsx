import { useEffect, useState } from "react";
import { Textarea } from "@planview/pv-form";
import { useUpdateItemName } from "@/hooks/useDocuments";

interface NameFieldProps {
  itemId: string;
  itemType: "document" | "folder";
  value: string | null;
}

export function NameField({ itemId, itemType, value }: NameFieldProps) {
  const [draft, setDraft] = useState(value ?? "");
  const { mutate: saveName } = useUpdateItemName();

  // sync draft when item changes
  useEffect(() => {
    setDraft(value ?? "");
  }, [itemId, value]);

  const handleBlur = () => {
    const trimmed = draft.trim();
    const next = trimmed || null;
    if (next !== value) {
      saveName({ id: itemId, type: itemType, name: next || "" });
    }
  };

  return (
    <Textarea label="Name" value={draft} onChange={(val) => setDraft(val)} onBlur={handleBlur} placeholder="name" />
  );
}
