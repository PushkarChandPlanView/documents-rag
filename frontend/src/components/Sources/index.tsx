import React, { useState } from "react";
import {
  ButtonEmpty, ButtonPrimary, DropdownMenu, ListItem, Modal, MODAL_LARGE,
} from "@planview/pv-uikit";
import { Community, Link as LinkIcon, Plus, Workspace } from "@planview/pv-icons";
import { CustomSlackIcon } from "@/customicons/slack";
import { JiraIcon } from "./constants";
import { SourceForm } from "./SourceForm";
import { SourceQueue } from "./SourceQueue";
import { Container, FooterRow, RightSection } from "./styled";
import type { QueueItem, Source } from "./types";

type Props = { onClose: () => void };

const AddSourcesModal = ({ onClose }: Props) => {
  const [isCreating, setIsCreating]     = useState<Source>(null);
  const [queue, setQueue]               = useState<QueueItem[]>([]);
  const [form, setForm]                 = useState<Record<string, string>>({});
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const field = (key: string) => ({
    value: form[key] ?? "",
    onChange: (val: string) => setForm(prev => ({ ...prev, [key]: val })),
  });

  const handleAddToQueue = () => {
    if (!isCreating) return;
    const item = { source: isCreating, ...form } as QueueItem;
    if (editingIndex !== null) {
      setQueue(prev => prev.map((q, i) => i === editingIndex ? item : q));
      setEditingIndex(null);
    } else {
      setQueue(prev => [...prev, item]);
    }
    setIsCreating(null);
    setForm({});
  };

  const handleEdit = (item: QueueItem, index: number) => {
    const { source, ...rest } = item;
    setForm(rest as Record<string, string>);
    setIsCreating(source);
    setEditingIndex(index);
  };

  const handleCancel = () => { setIsCreating(null); setForm({}); setEditingIndex(null); };

  const Footer = () => (
    <FooterRow>
      <ButtonEmpty onClick={isCreating ? handleCancel : onClose}>
        {isCreating ? "Back" : "Cancel"}
      </ButtonEmpty>
      <RightSection>
        {isCreating ? (
          <ButtonPrimary onClick={handleAddToQueue}>
            {editingIndex !== null ? "Save Changes" : "Add to Queue"}
          </ButtonPrimary>
        ) : (
          <>
            <DropdownMenu
              label="add-source-menu"
              trigger={(props) => (
                <ButtonPrimary activated={props["aria-expanded"]} {...props} withCaret icon={<Plus />}>
                  Add Source
                </ButtonPrimary>
              )}
            >
              <ListItem label="Jira"       icon={<JiraIcon />}        onActivate={() => setIsCreating("jira")}       />
              <ListItem label="Confluence" icon={<Workspace />}       onActivate={() => setIsCreating("confluence")} />
              <ListItem label="Github"     icon={<Community />}       onActivate={() => setIsCreating("github")}     />
              <ListItem label="Slack"      icon={<CustomSlackIcon />} onActivate={() => setIsCreating("slack")}      />
              <ListItem label="Link"       icon={<LinkIcon />}        onActivate={() => setIsCreating("link")}       />
            </DropdownMenu>
            <ButtonPrimary disabled={queue.length === 0}>
              Index All{queue.length > 0 ? ` (${queue.length})` : ""}
            </ButtonPrimary>
          </>
        )}
      </RightSection>
    </FooterRow>
  );

  return (
    <Modal headerText="Add Data Source" size={MODAL_LARGE} onCancel={onClose} Footer={Footer}>
      <Container>
        {isCreating
          ? <SourceForm source={isCreating} field={field} />
          : <SourceQueue
              queue={queue}
              onEdit={handleEdit}
              onRemove={(i) => setQueue(prev => prev.filter((_, idx) => idx !== i))}
            />
        }
      </Container>
    </Modal>
  );
};

export default AddSourcesModal;
