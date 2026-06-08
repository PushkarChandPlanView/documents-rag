import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import type { InfiniteData } from "@tanstack/react-query";
import type { UnifiedListResponse } from "@/types";
import { documentsApi } from "@/api/documents";
import { queryClient } from "@/store/queryClient";

export function useDocuments(parentId?: string, limit = 50) {
  return useInfiniteQuery({
    queryKey: ["documents", parentId ?? "root"],
    queryFn: ({ pageParam }) => documentsApi.list(pageParam as string | null, limit, parentId),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.has_more ? lastPage.next_cursor : undefined,
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => documentsApi.get(id),
    enabled: !!id,
  });
}

export function useItemDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: async () => {
      const doc = await documentsApi.get(id!);
      // Map DocumentDetailResponse → UnifiedItem so DetailsPane can render on refresh
      const item: import("@/types").UnifiedItem = {
        type: "document",
        id: doc.id,
        name: doc.name ?? doc.filename,
        filename: doc.filename,
        description: doc.description,
        parent_id: doc.folder_id,
        parent_name: doc.folder_name,
        folder_id: null,
        mime_type: doc.mime_type,
        file_size_bytes: doc.file_size_bytes,
        status: doc.status,
        source_url: doc.source_url,
        processing_jobs: doc.processing_jobs,
        compliance_status: null,
        created_at: doc.created_at,
        updated_at: doc.updated_at,
      };
      return item;
    },
    enabled: !!id,
  });
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: ({
      file,
      onProgress,
      folderId,
    }: {
      file: File;
      onProgress?: (p: number) => void;
      folderId?: string;
    }) => documentsApi.upload(file, onProgress, folderId),
  });
}

export function useAddLink() {
  return useMutation({
    mutationFn: ({
      url,
      title,
      folderId,
    }: {
      url: string;
      title?: string;
      folderId?: string;
    }) => documentsApi.addLink(url, title, folderId),
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

export function useDeleteFolder() {
  return useMutation({
    mutationFn: (id: string) => documentsApi.deleteFolder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}


export function useUpdateItemName() {
  return useMutation({
    mutationFn: ({ id, type, name }: { id: string; type: "document" | "folder"; name: string }) =>
      type === "folder"
        ? documentsApi.updateFolder(id, { name })
        : documentsApi.updateDocument(id, { name }),
    onMutate: async ({ id, name }) => {
      await queryClient.cancelQueries({ queryKey: ["documents"] });
      queryClient.setQueriesData<InfiniteData<UnifiedListResponse>>(
        { queryKey: ["documents"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((item) =>
                item.id === id
                  ? item.type === "folder"
                    ? { ...item, name }
                    : { ...item, filename: name }
                  : item
              ),
            })),
          };
        },
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useReprocessDocument() {
  return useMutation({
    mutationFn: (id: string) => documentsApi.reprocess(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useUpdateDescription() {
  return useMutation({
    mutationFn: ({ id, type, description }: { id: string; type: "document" | "folder"; description: string | null }) =>
      type === "folder"
        ? documentsApi.updateFolder(id, { description })
        : documentsApi.updateDocument(id, { description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
