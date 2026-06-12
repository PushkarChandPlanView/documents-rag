import { useRef, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import {
  Toolbar,
  ToolbarSectionLeft,
  ToolbarSectionRight,
} from "@planview/pv-toolbar";
import { ButtonEmpty, ButtonPrimary, Chip, Input, Textarea } from "@planview/pv-uikit";
import type { ComboboxOption } from "@planview/pv-uikit";
import { Community, Workspace } from "@planview/pv-icons";
import { Combobox, Field } from "@planview/pv-form";
import { apiClient } from "@/api/client";
import { CustomSlackIcon } from "@/customicons/slack";
import { JiraIcon } from "@/components/Sources/constants";
import { buildFile } from "@/components/Sources/builders";
import type { SourceType } from "@/components/Sources/builders";

// ── Source tab definitions ─────────────────────────────────────────────────────

const TABS: { id: SourceType; label: string; icon: React.ReactNode }[] = [
  { id: "jira",       label: "Jira",       icon: <JiraIcon /> },
  { id: "confluence", label: "Confluence", icon: <Workspace /> },
  { id: "hubspot",    label: "HubSpot",    icon: <HubSpotIcon /> },
  { id: "slack",      label: "Slack",      icon: <CustomSlackIcon /> },
  { id: "github",     label: "GitHub",     icon: <Community /> },
];

function HubSpotIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
      <path d="M18.16 8.75V6.37a2.1 2.1 0 0 0 1.22-1.9V4.4a2.1 2.1 0 0 0-2.1-2.1h-.07a2.1 2.1 0 0 0-2.1 2.1v.07a2.1 2.1 0 0 0 1.22 1.9v2.38a5.96 5.96 0 0 0-2.83 1.24L7.2 5.78a2.34 2.34 0 1 0-.9 1.04l6.1 3.95a5.97 5.97 0 0 0-.84 3.08 5.97 5.97 0 0 0 .94 3.25l-1.85 1.85a1.8 1.8 0 1 0 1.06 1.06l1.8-1.8a5.97 5.97 0 0 0 3.7 1.27 5.99 5.99 0 1 0-1.05-11.93zm1.05 9.5a3.54 3.54 0 1 1 0-7.08 3.54 3.54 0 0 1 0 7.08z" />
    </svg>
  );
}

// ── Styled components ─────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
`;

const Body = styled.div`
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: ${spacing.large}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.large}px;
`;

const TabRow = styled.div`
  display: flex;
  gap: 2px;
  border-bottom: 2px solid ${color.borderLight};
  flex-shrink: 0;
`;

const Tab = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: ${({ $active }) => ($active ? "700" : "400")};
  color: ${({ $active }) => ($active ? color.textPrimary : color.textSecondary)};
  border-bottom: 2px solid ${({ $active }) => ($active ? color.blue400 ?? "#1565c0" : "transparent")};
  margin-bottom: -2px;
  transition: color 0.12s;
  svg { width: 16px; height: 16px; flex-shrink: 0; }
  &:hover { color: ${color.textPrimary}; }
`;

const FormCard = styled.div`
  background: ${color.backgroundNeutral0};
  border: 1px solid ${color.borderLight};
  border-radius: 8px;
  padding: ${spacing.large}px;
`;

const FormGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${spacing.medium}px ${spacing.large}px;
`;

const FullWidth = styled.div`
  grid-column: 1 / -1;
`;

const FormActions = styled.div`
  display: flex;
  gap: ${spacing.small}px;
  justify-content: flex-end;
  margin-top: ${spacing.medium}px;
  padding-top: ${spacing.medium}px;
  border-top: 1px solid ${color.borderLight};
`;

const SectionTitle = styled.h2`
  margin: 0;
  ${text.regularSemibold}
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: ${color.textSecondary};
  font-size: 11px;
`;

const QueueTable = styled.div`
  background: ${color.backgroundNeutral0};
  border: 1px solid ${color.borderLight};
  border-radius: 8px;
  overflow: hidden;
`;

const QueueHeader = styled.div`
  display: grid;
  grid-template-columns: 1fr 100px 90px 80px;
  padding: 8px 14px;
  background: ${color.backgroundNeutral50};
  border-bottom: 1px solid ${color.borderLight};
  font-size: 11px;
  font-weight: 700;
  color: ${color.textSecondary};
`;

const QueueRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 100px 90px 80px;
  padding: 8px 14px;
  border-bottom: 1px solid ${color.borderLight};
  align-items: center;
  font-size: 12px;
  &:last-child { border-bottom: none; }
`;

const FileName = styled.span`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: ${color.textPrimary};
`;

const ToolbarTitle = styled.span`
  ${text.small};
  font-weight: 700;
`;

const EmptyQueue = styled.div`
  padding: ${spacing.large}px;
  text-align: center;
  ${text.small}
  color: ${color.textSecondary};
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

function sel(options: ComboboxOption[], val: string): ComboboxOption | null {
  return options.find((o) => o.value === val) ?? options[0] ?? null;
}

type QueueItem = {
  name: string;
  sourceType: SourceType;
  status: "queued" | "uploading" | "done" | "error";
  docId?: string;
  error?: string;
};

// ── Per-source forms ──────────────────────────────────────────────────────────

function JiraForm({ onSubmit, submitting }: FormProps) {
  const f = useFormState();
  const ISSUE_TYPES: ComboboxOption[] = [
    { value: "Bug", label: "Bug" }, { value: "Task", label: "Task" },
    { value: "Story", label: "Story" }, { value: "Incident", label: "Incident" },
    { value: "Epic", label: "Epic" },
  ];
  const STATUSES: ComboboxOption[] = [
    { value: "Open", label: "Open" }, { value: "In Progress", label: "In Progress" },
    { value: "Review", label: "Review" }, { value: "Resolved", label: "Resolved" },
    { value: "Closed", label: "Closed" },
  ];
  const PRIORITIES: ComboboxOption[] = [
    { value: "P0", label: "P0" }, { value: "P1", label: "P1" },
    { value: "P2", label: "P2" }, { value: "P3", label: "P3" },
  ];

  const valid = !!(f.v("key") && f.v("project") && f.v("summary") && f.v("description"));

  return (
    <FormCard>
      <FormGrid>
        <TF id="jira-key"     label="Key *"        placeholder="PP-1042"                        value={f.v("key")}     onChange={f.s("key")} />
        <TF id="jira-project" label="Project *"    placeholder="projectplace-platform"          value={f.v("project")} onChange={f.s("project")} />
        <SF id="jira-type"    label="Issue Type *" value={f.v("issue_type") || "Bug"} onChange={f.s("issue_type")} options={ISSUE_TYPES} />
        <SF id="jira-status"  label="Status"       value={f.v("status") || "Open"}   onChange={f.s("status")}     options={STATUSES} />
        <SF id="jira-priority" label="Priority"    value={f.v("priority") || "P2"}   onChange={f.s("priority")}   options={PRIORITIES} />
        <TF id="jira-reporter" label="Reporter"    placeholder="name@planview.com"              value={f.v("reporter")} onChange={f.s("reporter")} />
        <FullWidth><TF id="jira-summary" label="Summary *" placeholder="Milestone dates not syncing on project board" value={f.v("summary")} onChange={f.s("summary")} /></FullWidth>
        <FullWidth><TAF id="jira-desc"   label="Description *" rows={5} placeholder="Steps to reproduce, expected vs actual behaviour in Projectplace…" value={f.v("description")} onChange={f.s("description")} /></FullWidth>
        <FullWidth><TF id="jira-labels"  label="Labels (comma-separated)" placeholder="board, milestone, card" value={f.v("labels")} onChange={f.s("labels")} /></FullWidth>
        <FullWidth><TAF id="jira-comments" label='Comments (one per line: "user: text")' rows={3} placeholder={"Alice: Reproduced on Q3 roadmap board.\nBob: Root cause in milestone date recalculation."} value={f.v("comments")} onChange={f.s("comments")} /></FullWidth>
      </FormGrid>
      <FormActions>
        <ButtonEmpty onClick={f.reset}>Clear</ButtonEmpty>
        <ButtonPrimary disabled={!valid || submitting} onClick={() => onSubmit("jira", f.data())}>
          {submitting ? "Indexing…" : "Index issue"}
        </ButtonPrimary>
      </FormActions>
    </FormCard>
  );
}

function ConfluenceForm({ onSubmit, submitting }: FormProps) {
  const f = useFormState();
  const STATUSES: ComboboxOption[] = [
    { value: "published", label: "Published" }, { value: "draft", label: "Draft" }, { value: "archived", label: "Archived" },
  ];
  const CONFIDENTIALITY: ComboboxOption[] = [
    { value: "internal", label: "Internal" }, { value: "confidential", label: "Confidential" }, { value: "public", label: "Public" },
  ];
  const valid = !!(f.v("title") && f.v("space") && f.v("content"));

  return (
    <FormCard>
      <FormGrid>
        <TF id="conf-title"  label="Title *"  placeholder="Projectplace Board Configuration Guide"  value={f.v("title")}  onChange={f.s("title")} />
        <TF id="conf-space"  label="Space *"  placeholder="projectplace-docs"                       value={f.v("space")}  onChange={f.s("space")} />
        <TF id="conf-author" label="Author"   placeholder="name@planview.com"                       value={f.v("author")} onChange={f.s("author")} />
        <SF id="conf-status"          label="Status"          value={f.v("status") || "published"}          onChange={f.s("status")}          options={STATUSES} />
        <SF id="conf-confidentiality" label="Confidentiality" value={f.v("confidentiality") || "internal"}  onChange={f.s("confidentiality")} options={CONFIDENTIALITY} />
        <FullWidth><TAF id="conf-content" label="Content *" rows={8} placeholder="How to set up boards, manage cards and milestones in Projectplace…" value={f.v("content")} onChange={f.s("content")} /></FullWidth>
        <FullWidth><TF id="conf-labels" label="Labels (comma-separated)" placeholder="projectplace, board, milestone" value={f.v("labels")} onChange={f.s("labels")} /></FullWidth>
      </FormGrid>
      <FormActions>
        <ButtonEmpty onClick={f.reset}>Clear</ButtonEmpty>
        <ButtonPrimary disabled={!valid || submitting} onClick={() => onSubmit("confluence", f.data())}>
          {submitting ? "Indexing…" : "Index page"}
        </ButtonPrimary>
      </FormActions>
    </FormCard>
  );
}

function HubSpotForm({ onSubmit, submitting }: FormProps) {
  const f = useFormState();
  const STAGES: ComboboxOption[] = [
    { value: "lead", label: "Lead" }, { value: "evaluation", label: "Evaluation" },
    { value: "negotiation", label: "Negotiation" }, { value: "customer", label: "Customer" },
    { value: "churned", label: "Churned" },
  ];
  const TIERS: ComboboxOption[] = [
    { value: "startup", label: "Startup" }, { value: "mid-market", label: "Mid-market" }, { value: "enterprise", label: "Enterprise" },
  ];
  const valid = !!(f.v("company_name") && f.v("company_domain"));

  return (
    <FormCard>
      <FormGrid>
        <TF id="hs-name"   label="Company Name *"   placeholder="Contoso Ltd"      value={f.v("company_name")}   onChange={f.s("company_name")} />
        <TF id="hs-domain" label="Company Domain *" placeholder="contoso.com"      value={f.v("company_domain")} onChange={f.s("company_domain")} />
        <SF id="hs-stage"  label="Stage"            value={f.v("stage") || "lead"} onChange={f.s("stage")}        options={STAGES} />
        <SF id="hs-tier"   label="Account Tier"     value={f.v("account_tier") || "startup"} onChange={f.s("account_tier")} options={TIERS} />
        <TF id="hs-industry" label="Industry"       placeholder="Professional Services" value={f.v("industry")}  onChange={f.s("industry")} />
        <TF id="hs-contacts" label="Contacts (comma-separated)" placeholder="Jane (PMO Lead), Tom (IT Director)" value={f.v("contacts")} onChange={f.s("contacts")} />
        <FullWidth><TAF id="hs-notes" label="Notes" rows={6} placeholder="Expanding Projectplace usage to 3 new teams; evaluating portfolio management add-on…" value={f.v("notes")} onChange={f.s("notes")} /></FullWidth>
        <FullWidth><TF id="hs-open-deals" label="Open Deals" placeholder="Projectplace Enterprise renewal — Q3 2026" value={f.v("open_deals")} onChange={f.s("open_deals")} /></FullWidth>
        <FullWidth><TF id="hs-labels"     label="Labels (comma-separated)" placeholder="projectplace, enterprise, renewal" value={f.v("labels")} onChange={f.s("labels")} /></FullWidth>
      </FormGrid>
      <FormActions>
        <ButtonEmpty onClick={f.reset}>Clear</ButtonEmpty>
        <ButtonPrimary disabled={!valid || submitting} onClick={() => onSubmit("hubspot", f.data())}>
          {submitting ? "Indexing…" : "Index account"}
        </ButtonPrimary>
      </FormActions>
    </FormCard>
  );
}

function SlackForm({ onSubmit, submitting }: FormProps) {
  const f = useFormState();
  const CHANNEL_TYPES: ComboboxOption[] = [
    { value: "public", label: "Public" }, { value: "private", label: "Private" }, { value: "dm", label: "DM" },
  ];
  const valid = !!(f.v("workspace") && f.v("channel") && f.v("title") && f.v("messages"));

  return (
    <FormCard>
      <FormGrid>
        <TF id="slack-workspace" label="Workspace *" placeholder="planview"           value={f.v("workspace")} onChange={f.s("workspace")} />
        <TF id="slack-channel"   label="Channel *"   placeholder="pp-product-team"   value={f.v("channel")}   onChange={f.s("channel")} />
        <SF id="slack-chtype"    label="Channel Type" value={f.v("channel_type") || "public"} onChange={f.s("channel_type")} options={CHANNEL_TYPES} />
        <TF id="slack-participants" label="Participants (comma-separated)" placeholder="alice, bob, charlie" value={f.v("participants")} onChange={f.s("participants")} />
        <FullWidth><TF id="slack-title" label="Thread Title *" placeholder="Card dependency view not loading on Projectplace board — 2026-06-01" value={f.v("title")} onChange={f.s("title")} /></FullWidth>
        <FullWidth><TAF id="slack-messages" label={'Messages * ("username: message", one per line)'} rows={7} placeholder={"alice: Board stuck loading when project has >200 cards.\nbob: Checking milestone calculation service now."} value={f.v("messages")} onChange={f.s("messages")} /></FullWidth>
        <TF id="slack-jira" label="Linked Jira Tickets (comma-separated)" placeholder="PP-1042, PP-1055" value={f.v("linked_jira_tickets")} onChange={f.s("linked_jira_tickets")} />
        <TF id="slack-prs"  label="Linked GitHub PRs (comma-separated)"   placeholder="planview/projectplace#789" value={f.v("linked_github_prs")}  onChange={f.s("linked_github_prs")} />
        <FullWidth><TF id="slack-labels" label="Labels (comma-separated)" placeholder="projectplace, board, milestone" value={f.v("labels")} onChange={f.s("labels")} /></FullWidth>
      </FormGrid>
      <FormActions>
        <ButtonEmpty onClick={f.reset}>Clear</ButtonEmpty>
        <ButtonPrimary disabled={!valid || submitting} onClick={() => onSubmit("slack", f.data())}>
          {submitting ? "Indexing…" : "Index thread"}
        </ButtonPrimary>
      </FormActions>
    </FormCard>
  );
}

function GitHubForm({ onSubmit, submitting }: FormProps) {
  const f = useFormState();
  const TYPES: ComboboxOption[] = [
    { value: "pull_request", label: "Pull Request" }, { value: "issue", label: "Issue" }, { value: "discussion", label: "Discussion" },
  ];
  const STATES: ComboboxOption[] = [
    { value: "open", label: "Open" }, { value: "closed", label: "Closed" }, { value: "merged", label: "Merged" },
  ];
  const valid = !!(f.v("repo") && f.v("number") && f.v("title") && f.v("body"));

  return (
    <FormCard>
      <FormGrid>
        <TF id="gh-repo"   label="Repository *" placeholder="planview/projectplace-web" value={f.v("repo")}   onChange={f.s("repo")} />
        <SF id="gh-type"   label="Type *"       value={f.v("type") || "pull_request"}  onChange={f.s("type")}  options={TYPES} />
        <TF id="gh-number" label="Number *"     placeholder="2341"                     value={f.v("number")} onChange={f.s("number")} />
        <SF id="gh-state"  label="State"        value={f.v("state") || "open"}         onChange={f.s("state")} options={STATES} />
        <TF id="gh-author" label="Author"       placeholder="alice"                    value={f.v("author")}      onChange={f.s("author")} />
        <TF id="gh-base"   label="Base Branch"  placeholder="main"                     value={f.v("base_branch")} onChange={f.s("base_branch")} />
        <FullWidth><TF id="gh-title"         label="Title *"             placeholder="Fix milestone date recalculation on multi-board projects" value={f.v("title")}         onChange={f.s("title")} /></FullWidth>
        <FullWidth><TAF id="gh-body"         label="Description / Body *" rows={6}     placeholder="Describes the board, card, or milestone behaviour being fixed and why…" value={f.v("body")} onChange={f.s("body")} /></FullWidth>
        <FullWidth><TF id="gh-labels"        label="Labels (comma-separated)"          placeholder="projectplace, board, milestone"   value={f.v("labels")}        onChange={f.s("labels")} /></FullWidth>
        <FullWidth><TF id="gh-files-changed" label="Files Changed (comma-separated)"   placeholder="src/board/milestone.ts, tests/milestone.test.ts" value={f.v("files_changed")} onChange={f.s("files_changed")} /></FullWidth>
        <FullWidth><TAF id="gh-comments"     label={'Comments ("username: comment", one per line)'} rows={3} placeholder={"alice: LGTM — tested on Q3 roadmap board\nbob: needs a test for >500 card projects"} value={f.v("comments")} onChange={f.s("comments")} /></FullWidth>
      </FormGrid>
      <FormActions>
        <ButtonEmpty onClick={f.reset}>Clear</ButtonEmpty>
        <ButtonPrimary disabled={!valid || submitting} onClick={() => onSubmit("github", f.data())}>
          {submitting ? "Indexing…" : "Index item"}
        </ButtonPrimary>
      </FormActions>
    </FormCard>
  );
}

// ── Shared form helpers ───────────────────────────────────────────────────────

type FormProps = {
  onSubmit: (source: SourceType, data: Record<string, string>) => void;
  submitting: boolean;
};

function useFormState() {
  const [state, setState] = useState<Record<string, string>>({});
  return {
    v: (key: string) => state[key] ?? "",
    s: (key: string) => (val: string) => setState((p) => ({ ...p, [key]: val })),
    reset: () => setState({}),
    data: () => ({ ...state }),
  };
}

// Lightweight wrappers to reduce verbosity
function TF({ id, label, placeholder, value, onChange }: {
  id: string; label: string; placeholder?: string;
  value: string; onChange: (v: string) => void;
}) {
  return (
    <Field id={id} label={label}>
      {(fp) => <Input {...fp} value={value} onChange={(v: string) => onChange(v)} placeholder={placeholder} />}
    </Field>
  );
}

function TAF({ id, label, placeholder, rows, value, onChange }: {
  id: string; label: string; placeholder?: string; rows?: number;
  value: string; onChange: (v: string) => void;
}) {
  return (
    <Field id={id} label={label}>
      {(fp) => (
        <Textarea
          {...fp}
          value={value}
          onChange={(v: string) => onChange(v)}
          placeholder={placeholder}
          nativeProps={{ rows: rows ?? 4 }}
        />
      )}
    </Field>
  );
}

function SF({ id, label, value, onChange, options }: {
  id: string; label: string; value: string;
  onChange: (v: string) => void; options: ComboboxOption[];
}) {
  return (
    <Combobox
      id={id}
      label={label}
      clearable={false}
      options={options}
      value={sel(options, value)}
      onChange={(o) => o && onChange(String(o.value))}
    />
  );
}

// ── Status chip ───────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<QueueItem["status"], string> = {
  queued:    "#e3f2fd",
  uploading: "#fff3e0",
  done:      "#e8f5e9",
  error:     "#ffebee",
};

// ── Page component ────────────────────────────────────────────────────────────

export default function SourceConfig() {
  const [activeTab, setActiveTab] = useState<SourceType>("jira");
  const [submitting, setSubmitting] = useState(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const queueRef = useRef(queue);
  queueRef.current = queue;

  async function handleSubmit(source: SourceType, data: Record<string, string>) {
    const file = buildFile(source, data);
    const queueItem: QueueItem = { name: file.name, sourceType: source, status: "uploading" };
    setQueue((prev) => [queueItem, ...prev]);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_type", source);

    setSubmitting(true);
    try {
      const res = await apiClient.post<{ document_id: string }>(
        "/documents/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 60_000 }
      );
      setQueue((prev) =>
        prev.map((q) =>
          q === queueItem ? { ...q, status: "done", docId: res.data.document_id } : q
        )
      );
    } catch (err) {
      const msg = (err as { message?: string }).message ?? "Upload failed";
      setQueue((prev) =>
        prev.map((q) => (q === queueItem ? { ...q, status: "error", error: msg } : q))
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageWrapper>
      <Toolbar label="Sources toolbar">
        <ToolbarSectionLeft>
          <ToolbarTitle>Sources</ToolbarTitle>
        </ToolbarSectionLeft>
        <ToolbarSectionRight moreMenuLabel="More actions"><span /></ToolbarSectionRight>
      </Toolbar>

      <Body>
        {/* Tab strip */}
        <TabRow>
          {TABS.map(({ id, label, icon }) => (
            <Tab key={id} $active={activeTab === id} onClick={() => setActiveTab(id)}>
              {icon}
              {label}
            </Tab>
          ))}
        </TabRow>

        {/* Per-source form */}
        {activeTab === "jira"       && <JiraForm       onSubmit={handleSubmit} submitting={submitting} />}
        {activeTab === "confluence" && <ConfluenceForm  onSubmit={handleSubmit} submitting={submitting} />}
        {activeTab === "hubspot"    && <HubSpotForm     onSubmit={handleSubmit} submitting={submitting} />}
        {activeTab === "slack"      && <SlackForm       onSubmit={handleSubmit} submitting={submitting} />}
        {activeTab === "github"     && <GitHubForm      onSubmit={handleSubmit} submitting={submitting} />}

        {/* Indexed queue */}
        <div>
          <SectionTitle style={{ marginBottom: spacing.small }}>Indexed this session ({queue.length})</SectionTitle>
          <QueueTable>
            {queue.length === 0 ? (
              <EmptyQueue>No documents indexed yet — fill in a form above and click Index.</EmptyQueue>
            ) : (
              <>
                <QueueHeader>
                  <span>File</span>
                  <span>Source</span>
                  <span>Status</span>
                  <span>Doc ID</span>
                </QueueHeader>
                {queue.map((item, i) => (
                  <QueueRow key={i}>
                    <FileName title={item.name}>{item.name}</FileName>
                    <span style={{ fontSize: 11, color: color.textSecondary, textTransform: "capitalize" }}>{item.sourceType}</span>
                    <Chip
                      label={item.status}
                      color={STATUS_COLOR[item.status]}
                      disabled
                    />
                    <span style={{ fontSize: 11, color: color.textSecondary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.docId ? item.docId.slice(0, 8) + "…" : item.error ? "error" : "—"}
                    </span>
                  </QueueRow>
                ))}
              </>
            )}
          </QueueTable>
        </div>
      </Body>
    </PageWrapper>
  );
}
