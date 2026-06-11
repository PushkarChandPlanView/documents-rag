import { Comment, CommentEditor } from "@planview/pv-editor";
import { AiAnvi, Edit, Trash } from "@planview/pv-icons";
import { ListItem } from "@planview/pv-uikit";
type Props = {
  documentId: string;
};

const CommentsTab = ({ documentId }: Props) => {
  return (
    <>
      <CommentEditor
        defaultValue=""
        onChange={() => {}}
        onSubmit={() => {}}
        placeholder="Add a comment. Type @ to mention someone."
      />
      {[1, 2, 4, 5].map((id) => (
        <Comment
          key={id}
          comment={{
            attachments: undefined,
            content:
              "<p>Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur. Quis autem vel eum iure reprehenderit. Vel illum qui dolorem eum fugiat quo voluptas nulla pariatur?</p>",
            createdBy: {
              avatar: "https://planview.projectplace.com/ppi/avatars/initial_avatar_PC.png",
              id: "1",
              name: "John Doe",
            },
            createdDate: new Date("2026-06-11T03:33:07.670Z"),
            id: "1",
            likedBy: undefined,
            pinnedBy: undefined,
          }}
          moreMenuItems={[
            <ListItem key="1" label="Edit" icon={<Edit />} />,
            <ListItem key="2" icon={<AiAnvi color="anvi" />} label="Implement" />,
            <ListItem key="3" label="Delete" icon={<Trash />} />,
          ]}
          onLike={() => {}}
        />
      ))}
    </>
  );
};

export default CommentsTab;
