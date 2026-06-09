import { useQuery } from "@tanstack/react-query";
import { editsApi } from "@/api/edits";

export function useDocumentEdits(documentId: string | undefined) {
  return useQuery({
    queryKey: ["edits", documentId],
    queryFn: () => editsApi.list(documentId!),
    enabled: !!documentId,
  });
}
