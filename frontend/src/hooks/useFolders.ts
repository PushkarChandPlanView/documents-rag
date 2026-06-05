import { useMutation, useQuery } from "@tanstack/react-query";
import { foldersApi } from "@/api/folders";
import { queryClient } from "@/store/queryClient";

export function useFolders(parentId?: string) {
  return useQuery({
    queryKey: ["folders", parentId ?? null],
    queryFn: () => foldersApi.list(parentId),
  });
}

export function useFolder(id: string) {
  return useQuery({
    queryKey: ["folder", id],
    queryFn: () => foldersApi.get(id),
    enabled: !!id,
  });
}

export function useFolderBreadcrumb(id: string) {
  return useQuery({
    queryKey: ["folder-breadcrumb", id],
    queryFn: () => foldersApi.breadcrumb(id),
    enabled: !!id,
  });
}

export function useCreateFolder() {
  return useMutation({
    mutationFn: ({ name, parentId }: { name: string; parentId?: string }) =>
      foldersApi.create(name, parentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteFolder() {
  return useMutation({
    mutationFn: (id: string) => foldersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
