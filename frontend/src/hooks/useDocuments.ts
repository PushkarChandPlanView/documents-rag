import { useMutation, useQuery } from "@tanstack/react-query";
import { documentsApi } from "@/api/documents";
import { queryClient } from "@/store/queryClient";

export function useDocuments(offset = 0, limit = 50) {
  return useQuery({
    queryKey: ["documents", offset, limit],
    queryFn: () => documentsApi.list(offset, limit),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasActive = items.some((d) => d.status === "PROCESSING" || d.status === "PENDING");
      return hasActive ? 3000 : false;
    },
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => documentsApi.get(id),
    enabled: !!id,
  });
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (p: number) => void;
    }) => documentsApi.upload(file, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
