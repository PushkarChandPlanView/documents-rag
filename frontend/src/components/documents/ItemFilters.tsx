import { useState } from "react";
import { FilterPanel, FilterSectionList } from "@planview/pv-filter";

// ── Static option lists ───────────────────────────────────────────────────────

const FILE_TYPE_OPTIONS = [
  { id: "pdf",        label: "PDF" },
  { id: "word",       label: "Word" },
  { id: "text",       label: "Text" },
  { id: "markdown",   label: "Markdown" },
  { id: "csv",        label: "CSV" },
  { id: "excel",      label: "Excel" },
  { id: "powerpoint", label: "PowerPoint" },
  { id: "image",      label: "Image" },
];

const STATUS_OPTIONS = [
  { id: "COMPLETED",  label: "Completed" },
  { id: "PROCESSING", label: "Processing" },
  { id: "PENDING",    label: "Pending" },
  { id: "FAILED",     label: "Failed" },
];

// ── Types ─────────────────────────────────────────────────────────────────────

export type ItemFiltersState = {
  fileTypeIds: Set<string>;
  statuses: Set<string>;
};

interface ItemFiltersProps {
  value: ItemFiltersState;
  onChange: (next: ItemFiltersState) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ItemFilters({ value, onChange }: ItemFiltersProps) {
  const [fileTypeExpanded, setFileTypeExpanded] = useState(true);
  const [statusExpanded, setStatusExpanded] = useState(true);

  const handleClear = () =>
    onChange({ fileTypeIds: new Set(), statuses: new Set() });

  return (
    <FilterPanel onClear={handleClear}>
      <FilterSectionList
        label="File Type"
        options={FILE_TYPE_OPTIONS}
        value={value.fileTypeIds}
        expanded={fileTypeExpanded}
        onExpandedChange={setFileTypeExpanded}
        onChange={(selected) => onChange({ ...value, fileTypeIds: selected })}
      />
      <FilterSectionList
        label="Status"
        options={STATUS_OPTIONS}
        value={value.statuses}
        expanded={statusExpanded}
        onExpandedChange={setStatusExpanded}
        onChange={(selected) => onChange({ ...value, statuses: selected })}
      />
    </FilterPanel>
  );
}
