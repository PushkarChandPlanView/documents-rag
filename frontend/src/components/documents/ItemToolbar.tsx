import React from "react";
import styled from "styled-components";
import { color, spacing, text, borderRadius } from "@planview/pv-utilities";
import {
  Toolbar,
  ToolbarButtonEmpty,
  ToolbarDropdownMenu,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  ToolbarSeparator,
} from "@planview/pv-toolbar";
import { ButtonAnviEmptyInverse, DropdownMenu, ListItem } from "@planview/pv-uikit";
import {
  Filter,
  Upload,
  PlusCircle,
  DotsHorizontal,
  Help,
  ResizeFull,
  Folder,
  FileText,
  FileWord,
  FileExcel,
  FilePowerpoint,
  Link,
  Home,
  ChevronRight,
} from "@planview/pv-icons";

export interface BreadcrumbItem {
  id: string;
  name: string;
}

interface ItemToolbarProps {
  onToggleFilter: () => void;
  onUpload: () => void;
  onCreateFolder: () => void;
  onAddLink: () => void;
  breadcrumb?: BreadcrumbItem[];
  onBreadcrumbNavigate?: (id: string | null) => void;
}

const BreadcrumbPath = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 1px;
  ${text.small};
  margin-left: 2px;
`;

const Sep = styled.span`
  display: inline-flex;
  align-items: center;
  color: ${color.textPlaceholder};
  svg { width: 12px; height: 12px; }
`;

const PathLink = styled.button`
  border: none;
  background: none;
  padding: 3px ${spacing.xsmall}px;
  ${borderRadius.small()};
  cursor: pointer;
  color: ${color.backgroundPrimary};
  ${text.small};
  line-height: 1;
  &:hover { background: rgba(0,0,0,0.05); text-decoration: underline; }
`;

const PathCurrent = styled.span`
  padding: 3px ${spacing.xsmall}px;
  font-weight: 600;
  ${text.small};
  color: ${color.textPrimary};
`;

export function ItemToolbar({
  onToggleFilter,
  onUpload,
  onCreateFolder,
  onAddLink,
  breadcrumb,
  onBreadcrumbNavigate,
}: ItemToolbarProps) {
  const visibleCrumbs = breadcrumb ? breadcrumb.slice(-2) : [];
  const hiddenCrumbs  = breadcrumb ? breadcrumb.slice(0, -2) : [];
  const hasBreadcrumb = breadcrumb && onBreadcrumbNavigate;

  return (
    <Toolbar label="Documents toolbar">
      <ToolbarSectionLeft>
        <ToolbarButtonEmpty
          icon={<Filter />}
          tooltip="Toggle filters"
          onClick={onToggleFilter}
        />
        <ToolbarSeparator />
        <ToolbarButtonEmpty
          icon={<Upload />}
          tooltip="Upload document"
          onClick={onUpload}
        />
        <ToolbarDropdownMenu
          label="Add"
          filterMode="auto"
          trigger={(props) => (
            <ToolbarButtonEmpty
              icon={<PlusCircle />}
              withCaret
              activated={props["aria-expanded"]}
              {...props}
            >
              Add
            </ToolbarButtonEmpty>
          )}
        >
          <ListItem icon={<Folder />}         label="Folder"               onActivate={onCreateFolder} />
          <ListItem icon={<FileText />}       label="Text document"        onActivate={onUpload} />
          <ListItem icon={<FileWord />}       label="Word document"        onActivate={onUpload} />
          <ListItem icon={<FileExcel />}      label="Microsoft Excel"      onActivate={onUpload} />
          <ListItem icon={<FilePowerpoint />} label="Microsoft PowerPoint" onActivate={onUpload} />
          <ListItem icon={<Link />}           label="Link"                 onActivate={onAddLink} />
        </ToolbarDropdownMenu>

        {hasBreadcrumb && (
          <>
            <DropdownMenu
              label="Navigate to ancestor"
              trigger={(props) => (
                <ButtonAnviEmptyInverse
                  icon={<Home />}
                  withCaret
                  {...props}
                />
              )}
            >
              <ListItem label="Home" onActivate={() => onBreadcrumbNavigate!(null)} />
              {hiddenCrumbs.map((crumb) => (
                <ListItem
                  key={crumb.id}
                  label={crumb.name}
                  onActivate={() => onBreadcrumbNavigate!(crumb.id)}
                />
              ))}
            </DropdownMenu>

            <BreadcrumbPath>
              {visibleCrumbs.map((crumb, i) => {
                const isLast = i === visibleCrumbs.length - 1;
                return (
                  <React.Fragment key={crumb.id}>
                    <Sep><ChevronRight /></Sep>
                    {isLast
                      ? <PathCurrent>{crumb.name}</PathCurrent>
                      : <PathLink onClick={() => onBreadcrumbNavigate!(crumb.id)}>{crumb.name}</PathLink>
                    }
                  </React.Fragment>
                );
              })}
            </BreadcrumbPath>

            <ToolbarSeparator />
          </>
        )}
      </ToolbarSectionLeft>

      <ToolbarSectionRight moreMenuLabel="More actions">
        <ToolbarButtonEmpty icon={<DotsHorizontal />} tooltip="More options" />
        <ToolbarButtonEmpty icon={<Help />} tooltip="Help" />
        <ToolbarButtonEmpty icon={<ResizeFull />} tooltip="Expand" />
      </ToolbarSectionRight>
    </Toolbar>
  );
}
