import { useRef, useState } from "react";
import { Comment, CommentEditor } from "@planview/pv-editor";
import type { CommentEditorApi } from "@planview/pv-editor";
import { AiAnvi, Edit, Trash } from "@planview/pv-icons";
import { ButtonEmpty, ListItem } from "@planview/pv-uikit";
import { color, text, spacing } from "@planview/pv-utilities";
import styled from "styled-components";
import {
  useComments,
  useCreateComment,
  useDeleteComment,
  useLikeComment,
  useUnlikeComment,
  useUpdateComment,
} from "@/hooks/useComments";
import type { CommentItem } from "@/types/comments";
import { useAuthStore } from "@/store/authStore";
import { editsApi, type DocumentEdit } from "@/api/edits";
import { EditDiffModal } from "@/components/chat/EditDiffModal";

type Props = { documentId: string };

// ── Styled ────────────────────────────────────────────────────────────────────

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
  padding: ${spacing.medium}px;
`;

const LoadMore = styled.div`
  display: flex;
  justify-content: center;
  padding: ${spacing.small}px 0;
`;

const Empty = styled.p`
  ${text.small};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px 0;
`;

const ErrorMsg = styled.p`
  ${text.small};
  color: ${color.error400};
  text-align: center;
`;
import { isActionable } from "../../../actionable";

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function getInitials(text: string): string {
  const words = text.trim().split(/\s+/).filter(Boolean);

  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  return words[0]?.slice(0, 2).toUpperCase() ?? "";
}
const getAvatar = (name: string) => {
  const initials = getInitials(name);
  return `https://ui-avatars.com/api/?name=${initials}&background=random`;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function toEditorComment(c: CommentItem) {
  return {
    attachments: undefined,
    content: c.content,
    createdBy: {
      avatar: c.author.avatar ?? getAvatar(c.author.name),
      id: c.author.id,
      name: c.author.name,
    },
    createdDate: new Date(c.created_at),
    id: c.id,
    // likedBy.User requires avatar — provide empty string when absent
    likedBy: c.liked_by_me ? [{ id: c.author.id, name: c.author.name, avatar: c.author.avatar ?? "" }] : undefined,
    pinnedBy: undefined,
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

const CommentsTab = ({ documentId }: Props) => {
  const userId = useAuthStore((s) => s.userId);
  // Store editor API refs so we can call getHTML() / clear() on submit
  const newEditorRef = useRef<CommentEditorApi | null>(null);
  const editEditorRef = useRef<CommentEditorApi | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [newHasContent, setNewHasContent] = useState(false);
  const [editHasContent, setEditHasContent] = useState(false);
  const [implementing, setImplementing] = useState(false);
  const [implementProposal, setImplementProposal] = useState<DocumentEdit | null>(null);

  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } = useComments(documentId);

  const { mutate: createComment } = useCreateComment(documentId);
  const { mutate: updateComment } = useUpdateComment(documentId);
  const { mutate: deleteComment } = useDeleteComment(documentId);
  const { mutate: likeComment } = useLikeComment(documentId);
  const { mutate: unlikeComment } = useUnlikeComment(documentId);

  const allComments = data?.pages.flatMap((p) => p.items) ?? [];

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleCreate = () => {
    const content = newEditorRef.current?.getValue() ?? "";
    if (!content.trim()) return;
    createComment(
      { document_id: documentId, content },
      {
        onSuccess: () => {
          newEditorRef.current?.clear();
          setNewHasContent(false);
        },
      },
    );
  };

  const handleSaveEdit = (commentId: string) => {
    const content = editEditorRef.current?.getValue() ?? "";
    if (!content.trim()) return;
    updateComment(
      { commentId, payload: { content } },
      {
        onSuccess: () => {
          setEditingId(null);
          setEditHasContent(false);
          editEditorRef.current?.clear();
        },
      },
    );
  };

  const handleLike = (item: CommentItem) => {
    if (item.liked_by_me) unlikeComment(item.id);
    else likeComment(item.id);
  };

  const handleImplement = async (content: string) => {
    setImplementing(true);
    try {
      const proposal = await editsApi.propose(documentId, content);
      setImplementProposal(proposal);
    } catch {
      // silently ignore — user can retry
    } finally {
      setImplementing(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (isError) return <ErrorMsg>Failed to load comments. Please try again.</ErrorMsg>;

  return (
    <>
    {implementing && <Empty>Generating edit preview…</Empty>}
    {implementProposal && (
      <EditDiffModal
        documentId={documentId}
        editId={implementProposal.id}
        instruction={implementProposal.instruction}
        proposedContent={implementProposal.proposed_content}
        initialStatus={implementProposal.status}
        onClose={() => setImplementProposal(null)}
        onStatusChange={() => setImplementProposal(null)}
      />
    )}
    {implementing && <Empty>Generating edit preview…</Empty>}
    <Wrapper>
      {/* ── Composer (hidden while editing an existing comment) ── */}
      {editingId === null && (
        <CommentEditor
          key="new"
          defaultValue=""
          onChange={(editor: CommentEditorApi) => {
            newEditorRef.current = editor;
            setNewHasContent(!editor.isEmpty());
          }}
          onSubmit={handleCreate}
          submitButtonEnabled={newHasContent}
          placeholder="Add a comment"
        />
      )}

      {isLoading && <Empty>Loading comments…</Empty>}

      {!isLoading && allComments.length === 0 && <Empty>No comments yet. Be the first to comment!</Empty>}

      {allComments.map((item) =>
        editingId === item.id ? (
          <CommentEditor
            key={`edit-${item.id}`}
            defaultValue={item.content}
            onChange={(editor: CommentEditorApi) => {
              editEditorRef.current = editor;
              setEditHasContent(!editor.isEmpty());
            }}
            onSubmit={() => handleSaveEdit(item.id)}
            submitButtonEnabled={editHasContent}
            placeholder="Edit your comment…"
          />
        ) : (
          <Comment
            key={item.id}
            comment={toEditorComment(item)}
            onLike={() => handleLike(item)}
            moreMenuItems={
              item.author.id === userId
                ? [
                    ...(isActionable(stripHtml(item.content)) ? [<ListItem key="ai" label="Implement" icon={<AiAnvi color="anvi" />} onActivate={() => handleImplement(stripHtml(item.content))} />] : []),
                    <ListItem key="edit" label="Edit" icon={<Edit />} onActivate={() => setEditingId(item.id)} />,
                    <ListItem key="delete" label="Delete" icon={<Trash />} onActivate={() => deleteComment(item.id)} />,
                  ]
                : isActionable(stripHtml(item.content)) ? [<ListItem key="ai" label="Implement" icon={<AiAnvi color="anvi" />} onActivate={() => handleImplement(stripHtml(item.content))} />] : undefined
            }
          />
        ),
      )}

      {hasNextPage && (
        <LoadMore>
          <ButtonEmpty onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "Loading…" : "Load more"}
          </ButtonEmpty>
        </LoadMore>
      )}
    </Wrapper>
    </>
  );
};

export default CommentsTab;
