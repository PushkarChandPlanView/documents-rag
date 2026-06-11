import { ButtonEmpty } from "@planview/pv-uikit";
import { Edit, Info, Trash } from "@planview/pv-icons";
import { SOURCE_ICON, getItemMeta } from "./constants";
import {
  EmptyState,
  InfoBanner,
  InfoSection,
  QueueHeaderCount, QueueHeaderRow, QueueHeaderTitle,
  QueueItemIconBox, QueueItemLabel, QueueItemRow, QueueItemSub, QueueItemText,
  QueueList,
} from "./styled";
import type { QueueItem } from "./types";
import { Textarea } from "@planview/pv-form";

interface SourceQueueProps {
  queue: QueueItem[];
  onEdit: (item: QueueItem, index: number) => void;
  onRemove: (index: number) => void;
}

export const SourceQueue = ({ queue, onEdit, onRemove }: SourceQueueProps) => {
  if (queue.length === 0) {
    return <EmptyState>No sources added yet — use "Add Source" to get started.</EmptyState>;
  }

  return (
    <>
      <QueueHeaderRow>
        <QueueHeaderTitle>Sources to Index</QueueHeaderTitle>
        <QueueHeaderCount>
          {queue.length} {queue.length === 1 ? "source" : "sources"} staged
        </QueueHeaderCount>
      </QueueHeaderRow>
      <QueueList>
        {queue.map((item, i) => (
          <QueueItemRow key={i}>
            <QueueItemIconBox>{SOURCE_ICON[item.source]}</QueueItemIconBox>
            <QueueItemText>
              <QueueItemLabel>{item.key || item.source}</QueueItemLabel>
              <QueueItemSub>{getItemMeta(item)}</QueueItemSub>
            </QueueItemText>
            <ButtonEmpty icon={<Edit />}  title="Edit"   onClick={() => onEdit(item, i)} />
            <ButtonEmpty icon={<Trash />} title="Remove" onClick={() => onRemove(i)} />
          </QueueItemRow>
        ))}
        <Textarea placeholder="Add prompts" label={"Prompts"} />
      </QueueList>
      <InfoSection>
        <InfoBanner>
          <Info />
          Indexing might take a few minutes depending on the data volume. You can monitor the progress in the Data Status dashboard.
        </InfoBanner>
      </InfoSection>
    </>
  );
};
