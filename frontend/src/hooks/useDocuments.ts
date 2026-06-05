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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
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
