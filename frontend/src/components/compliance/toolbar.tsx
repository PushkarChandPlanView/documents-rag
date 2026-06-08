import styled from "styled-components";
import { spacing, text } from "@planview/pv-utilities";
import {
  Toolbar,
  ToolbarButtonEmpty,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  ToolbarSeparator,
} from "@planview/pv-toolbar";
import { ButtonEmpty, ButtonPrimary } from "@planview/pv-uikit";
import { DotsHorizontal, Help, ResizeFull } from "@planview/pv-icons";

const Title = styled.span`
  ${text.small};
  font-weight: 700;
`;

const DirtyBadge = styled.span`
  ${text.small};
  font-weight: 600;
  color: #e65100;
  background: #fff3e0;
  padding: 2px 10px;
  border-radius: 12px;
`;


const ActionGroup = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.xsmall}px;
`;

export interface ToolbarProps {
  isAdmin: boolean;
  dirtyCount: number;
  saving: boolean;
  onApply: () => void;
  onReset: () => void;
  onAddRule: () => void;
}

export function ComplianceToolbar({
  isAdmin,
  dirtyCount,
  saving,
  onApply,
  onReset,
  onAddRule,
}: ToolbarProps) {
  const isDirty = dirtyCount > 0;

  return (
    <Toolbar label="Compliance toolbar">
      <ToolbarSectionLeft>
        <Title>Compliance</Title>
        <ToolbarSeparator />
        <ButtonEmpty onClick={onAddRule}>+ Add Rule</ButtonEmpty>
        <ToolbarSeparator />
        {isDirty && (
          <DirtyBadge>
            {dirtyCount} unsaved change{dirtyCount > 1 ? "s" : ""}
          </DirtyBadge>
        )}
      </ToolbarSectionLeft>

      <ToolbarSectionRight moreMenuLabel="More actions">
        {isAdmin && (
          <ActionGroup>
            {isDirty && (
              <>
                <ButtonEmpty onClick={onReset} disabled={saving}>
                  Reset
                </ButtonEmpty>
                <ButtonPrimary onClick={onApply} disabled={saving}>
                  {saving
                    ? "Applying…"
                    : `Apply ${dirtyCount} Change${dirtyCount > 1 ? "s" : ""}`}
                </ButtonPrimary>
                <ToolbarSeparator />
              </>
            )}
           
          </ActionGroup>
        )}
        <ToolbarButtonEmpty icon={<DotsHorizontal />} tooltip="More options" />
        <ToolbarButtonEmpty icon={<Help />} tooltip="Help" />
        <ToolbarButtonEmpty icon={<ResizeFull />} tooltip="Expand" />
      </ToolbarSectionRight>
    </Toolbar>
  );
}
