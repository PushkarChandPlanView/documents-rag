import { useState } from "react";
import styled from "styled-components";
import { spacing } from "@planview/pv-utilities";
import { GENERIC, Modal, MODAL_LARGE, Checkbox } from "@planview/pv-uikit";
import { Field, Combobox } from "@planview/pv-form";
import { Input, Textarea } from "@planview/pv-uikit";
import type { ComboboxOption } from "@planview/pv-uikit";
import { useCreateAgent, useUpdateAgent } from "@/hooks/useAgents";
import type { Agent, AgentCreate, AgentTool, OutputFormat } from "@/types/agent";

const FieldsContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.xsmall}px;
`;

const SectionLabel = styled.div`
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #1565c0;
  margin-top: ${spacing.small}px;
  margin-bottom: ${spacing.xsmall}px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e3f2fd;
`;

const ToolsGrid = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${spacing.xsmall}px;
`;

const ToolRow = styled.label`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: #fff;
  user-select: none;
`;

const OUTPUT_OPTIONS: ComboboxOption[] = [
  { value: "markdown", label: "Markdown" },
  { value: "text", label: "Plain text" },
  { value: "json", label: "JSON" },
  { value: "planview", label: "Planview Board (auto-create)" },
];

const ITER_OPTIONS: ComboboxOption[] = [
  { value: "3", label: "3 iterations" },
  { value: "5", label: "5 iterations" },
  { value: "10", label: "10 iterations" },
];

const ALL_TOOLS: { value: AgentTool; label: string }[] = [
  { value: "search_all", label: "search_all (all sources)" },
  { value: "search_jira", label: "search_jira" },
  { value: "search_confluence", label: "search_confluence" },
  { value: "search_slack", label: "search_slack" },
  { value: "search_github", label: "search_github" },
  { value: "search_hubspot", label: "search_hubspot" },
];

interface Props {
  agent?: Agent;
  onClose: () => void;
}

export function AgentFormModal({ agent, onClose }: Props) {
  const { mutate: create, isPending: creating } = useCreateAgent();
  const { mutate: update, isPending: updating } = useUpdateAgent();
  const isPending = creating || updating;

  const [name, setName] = useState(agent?.name ?? "");
  const [description, setDescription] = useState(agent?.description ?? "");
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? "");
  const [format, setFormat] = useState<OutputFormat>(agent?.output_format ?? "markdown");
  const [tools, setTools] = useState<Set<AgentTool>>(
    new Set(agent?.tools ?? ["search_all"])
  );
  const [maxIter, setMaxIter] = useState(agent?.max_iter ?? 3);

  const isValid = name.trim().length > 0 && prompt.trim().length > 0 && tools.size > 0;

  function toggleTool(tool: AgentTool, checked: boolean) {
    setTools((prev) => {
      const next = new Set(prev);
      if (tool === "search_all") {
        // selecting search_all clears individual tools
        if (checked) {
          return new Set<AgentTool>(["search_all"]);
        } else {
          next.delete("search_all");
          return next;
        }
      }
      // selecting an individual tool removes search_all
      if (checked) {
        next.delete("search_all");
        next.add(tool);
      } else {
        next.delete(tool);
      }
      return next;
    });
  }

  function handleSubmit(_e: React.FormEvent<HTMLFormElement>) {
    const payload: AgentCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      system_prompt: prompt.trim(),
      output_format: format,
      tools: Array.from(tools),
      max_iter: maxIter,
    };
    if (agent) {
      update({ id: agent.id, data: payload }, { onSuccess: onClose });
    } else {
      create(payload, { onSuccess: onClose });
    }
    return false;
  }

  return (
    <Modal
      type={GENERIC}
      size={MODAL_LARGE}
      headerText={agent ? `Edit — ${agent.name}` : "New agent"}
      confirmText={isPending ? "Saving…" : "Save agent"}
      cancelText="Cancel"
      disableConfirm={!isValid || isPending}
      onCancel={onClose}
      asForm
      onConfirm={handleSubmit}
    >
      <FieldsContainer>
        <SectionLabel>Agent details</SectionLabel>

        <Field id="agent-name" label={{ text: "Name", required: true }}>
          {(fp) => (
            <Input
              {...fp}
              value={name}
              placeholder="e.g. Forge Incident Researcher"
              onChange={(v: string) => setName(v)}
            />
          )}
        </Field>

        <Field id="agent-desc" label="Description">
          {(fp) => (
            <Input
              {...fp}
              value={description}
              placeholder="Short summary of what this agent does"
              onChange={(v: string) => setDescription(v)}
            />
          )}
        </Field>

        <SectionLabel>System prompt</SectionLabel>

        <Field id="agent-prompt" label={{ text: "Instructions", required: true }}>
          {(fp) => (
            <Textarea
              {...fp}
              value={prompt}
              placeholder="You are a Forge engineering assistant. Research incidents and features using all available sources…"
              onChange={(v: string) => setPrompt(v)}
              nativeProps={{ rows: 5 }}
            />
          )}
        </Field>

        <SectionLabel>Output &amp; tools</SectionLabel>

        <Combobox
          id="agent-format"
          label="Output format"
          clearable={false}
          options={OUTPUT_OPTIONS}
          value={OUTPUT_OPTIONS.find((o) => o.value === format) ?? OUTPUT_OPTIONS[0]}
          onChange={(o) => o && setFormat(o.value as OutputFormat)}
        />

        <Combobox
          id="agent-iter"
          label="Max iterations"
          clearable={false}
          options={ITER_OPTIONS}
          value={ITER_OPTIONS.find((o) => String(o.value) === String(maxIter)) ?? ITER_OPTIONS[0]}
          onChange={(o) => o && setMaxIter(parseInt(String(o.value), 10))}
        />

        <Field id="agent-tools" label={{ text: "Tools", required: true }}>
          {() => (
            <ToolsGrid>
              {ALL_TOOLS.map(({ value, label }) => (
                <ToolRow key={value}>
                  <Checkbox
                    selected={tools.has(value)}
                    onChange={(checked) => toggleTool(value, checked)}
                    aria-label={label}
                  />
                  {label}
                </ToolRow>
              ))}
            </ToolsGrid>
          )}
        </Field>
      </FieldsContainer>
    </Modal>
  );
}
