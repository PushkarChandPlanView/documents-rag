import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { commentsApi } from "@/api/comments";
import type { CommentCreate, CommentItem, CommentUpdate, PaginatedComments } from "@/types/comments";

// ── Query keys ────────────────────────────────────────────────────────────────

export const commentKeys = {
  all: ["comments"] as const,
  list: (documentId: string) => [...commentKeys.all, "list", documentId] as const,
};

// ── List with infinite scroll ─────────────────────────────────────────────────

export function useComments(documentId: string) {
  return useInfiniteQuery<PaginatedComments, Error>({
    queryKey: commentKeys.list(documentId),
    queryFn: ({ pageParam = 1 }) =>
      commentsApi.list(documentId, pageParam as number),
    getNextPageParam: (last) =>
      last.has_next ? last.page + 1 : undefined,
    initialPageParam: 1,
    enabled: !!documentId,
  });
}

// ── Create ────────────────────────────────────────────────────────────────────

export function useCreateComment(documentId: string) {
  const qc = useQueryClient();
  return useMutation<CommentItem, Error, CommentCreate>({
    mutationFn: commentsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: commentKeys.list(documentId) }),
  });
}

// ── Update ────────────────────────────────────────────────────────────────────

export function useUpdateComment(documentId: string) {
  const qc = useQueryClient();
  return useMutation<CommentItem, Error, { commentId: string; payload: CommentUpdate }>({
    mutationFn: ({ commentId, payload }) => commentsApi.update(commentId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: commentKeys.list(documentId) }),
  });
}

// ── Delete ────────────────────────────────────────────────────────────────────

export function useDeleteComment(documentId: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: commentsApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: commentKeys.list(documentId) }),
  });
}

// ── Like / Unlike (optimistic) ────────────────────────────────────────────────

type LikeMutationContext = { previous: PaginatedComments[] | undefined };

function patchLike(
  pages: PaginatedComments[],
  commentId: string,
  delta: 1 | -1,
): PaginatedComments[] {
  return pages.map((page) => ({
    ...page,
    items: page.items.map((c) => patchComment(c, commentId, delta)),
  }));
}

function patchComment(c: CommentItem, id: string, delta: 1 | -1): CommentItem {
  if (c.id === id) {
    return {
      ...c,
      like_count: c.like_count + delta,
      liked_by_me: delta === 1,
    };
  }
  return {
    ...c,
    replies: c.replies.map((r) => patchComment(r, id, delta)),
  };
}

export function useLikeComment(documentId: string) {
  const qc = useQueryClient();
  const key = commentKeys.list(documentId);

  return useMutation<void, Error, string, LikeMutationContext>({
    mutationFn: commentsApi.like,
    onMutate: async (commentId) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<{ pages: PaginatedComments[] }>(key)?.pages;
      qc.setQueryData<{ pages: PaginatedComments[] }>(key, (old) =>
        old ? { ...old, pages: patchLike(old.pages, commentId, 1) } : old
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous)
        qc.setQueryData<{ pages: PaginatedComments[] }>(key, (old) =>
          old ? { ...old, pages: ctx.previous! } : old
        );
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export function useUnlikeComment(documentId: string) {
  const qc = useQueryClient();
  const key = commentKeys.list(documentId);

  return useMutation<void, Error, string, LikeMutationContext>({
    mutationFn: commentsApi.unlike,
    onMutate: async (commentId) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<{ pages: PaginatedComments[] }>(key)?.pages;
      qc.setQueryData<{ pages: PaginatedComments[] }>(key, (old) =>
        old ? { ...old, pages: patchLike(old.pages, commentId, -1) } : old
      );
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous)
        qc.setQueryData<{ pages: PaginatedComments[] }>(key, (old) =>
          old ? { ...old, pages: ctx.previous! } : old
        );
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}
