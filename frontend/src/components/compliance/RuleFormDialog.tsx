import { useState } from "react";
import styled from "styled-components";
import { spacing } from "@planview/pv-utilities";
import { GENERIC, Input, InputNumeric, Modal, MODAL_MEDIUM, Textarea } from "@planview/pv-uikit";
import type { ComboboxOption } from "@planview/pv-uikit";
import { Combobox, Field } from "@planview/pv-form";
import type { ComplianceRule, ComplianceRuleCreate, RuleType, Severity } from "@/types/compliance";
import { useCreateRule, useUpdateRule } from "@/hooks/useCompliance";

// ── Styles ────────────────────────────────────────────────────────────────────

const FieldsContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.xsmall}px;
`;

// ── Constants ─────────────────────────────────────────────────────────────────

const RULE_TYPE_OPTIONS: ComboboxOption[] = [
  { value: "keyword_required", label: "Keyword Required" },
  { value: "keyword_forbidden", label: "Keyword Forbidden" },
  { value: "age_limit_days", label: "Age Limit (Days)" },
  { value: "llm_check", label: "LLM Policy Check" },
];

const SEVERITY_OPTIONS: ComboboxOption[] = [
  { value: "info",     label: "Info — informational, no action required" },
  { value: "warning",  label: "Warning — should be addressed" },
  { value: "high",     label: "High — significant concern, needs remediation" },
  { value: "critical", label: "Critical — legal / security / privacy risk" },
];

const LLM_CONTENT_OPTIONS: ComboboxOption[] = [
  {
    value: "summary",
    label: "Document Summary — faster, good for tone and quality checks",
  },
  {
    value: "chunks",
    label: "Full Document Text — slower, needed for offensive language or duplicate detection",
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  rule?: ComplianceRule;
  onClose: () => void;
}

export function RuleFormDialog({ rule, onClose }: Props) {
  const { mutate: create, isPending: creating } = useCreateRule();
  const { mutate: update, isPending: updating } = useUpdateRule();
  const isPending = creating || updating;

  const [name, setName] = useState(rule?.name ?? "");
  const [description, setDescription] = useState(rule?.description ?? "");
  const [ruleType, setRuleType] = useState<RuleType>(rule?.rule_type ?? "keyword_forbidden");
  const [severity, setSeverity] = useState<Severity>(rule?.severity ?? "warning");
  const [keywords, setKeywords] = useState(
    Array.isArray((rule?.params as { keywords?: string[] })?.keywords)
      ? (rule?.params as { keywords: string[] }).keywords.join(", ")
      : ""
  );
  const [days, setDays] = useState<number>(
    (rule?.params as { days?: number })?.days ?? 365
  );
  const [policy, setPolicy] = useState(
    (rule?.params as { policy?: string })?.policy ?? ""
  );
  const [llmContent, setLlmContent] = useState<"summary" | "chunks">(
    (rule?.params as { content?: "summary" | "chunks" })?.content ?? "summary"
  );

  function buildParams(): Record<string, unknown> {
    if (ruleType === "keyword_required" || ruleType === "keyword_forbidden") {
      return { keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean) };
    }
    if (ruleType === "age_limit_days") {
      return { days };
    }
    return { policy, content: llmContent };
  }

  function handleSubmit(_e: React.FormEvent<HTMLFormElement>) {
    const params = buildParams();
    if (rule) {
      update(
        { id: rule.id, data: { name, description: description || undefined, params, severity } },
        { onSuccess: onClose }
      );
    } else {
      const data: ComplianceRuleCreate = {
        name,
        description: description || undefined,
        rule_type: ruleType,
        params,
        severity,
      };
      create(data, { onSuccess: onClose });
    }
    return false;
  }

  const isValid = name.trim().length > 0;

  return (
    <Modal
      type={GENERIC}
      size={MODAL_MEDIUM}
      headerText={rule ? "Edit Compliance Rule" : "New Compliance Rule"}
      confirmText={isPending ? "Saving…" : "Save Rule"}
      cancelText="Cancel"
      disableConfirm={!isValid || isPending}
      onCancel={onClose}
      asForm
      onConfirm={handleSubmit}
    >
      <FieldsContainer>

        {/* Name */}
        <Field id="rule-name" label={{ text: "Name", required: true }}>
          {(fieldProps) => (
            <Input
              {...fieldProps}
              value={name}
              placeholder="e.g. No PII — SSN"
              onChange={(val: string) => setName(val)}
            />
          )}
        </Field>

        {/* Description */}
        <Field id="rule-description" label="Description">
          {(fieldProps) => (
            <Input
              {...fieldProps}
              value={description}
              placeholder="Optional — shown in the rules table"
              onChange={(val: string) => setDescription(val)}
            />
          )}
        </Field>

        {/* Rule Type — Combobox (self-contained, not editable on edit) */}
        {!rule && (
          <Combobox
            id="rule-type"
            label="Rule Type"
            clearable={false}
            options={RULE_TYPE_OPTIONS}
            value={RULE_TYPE_OPTIONS.find((o) => o.value === ruleType) ?? null}
            onChange={(option) => option && setRuleType(option.value as RuleType)}
          />
        )}

        {/* Severity — Combobox (self-contained) */}
        <Combobox
          id="rule-severity"
          label="Severity"
          clearable={false}
          options={SEVERITY_OPTIONS}
          value={SEVERITY_OPTIONS.find((o) => o.value === severity) ?? null}
          onChange={(option) => option && setSeverity(option.value as Severity)}
        />

        {/* Keywords (keyword_required / keyword_forbidden) */}
        {(ruleType === "keyword_required" || ruleType === "keyword_forbidden") && (
          <Field id="rule-keywords" label="Keywords (comma-separated)">
            {(fieldProps) => (
              <Input
                {...fieldProps}
                value={keywords}
                placeholder="e.g. disclaimer, confidential"
                onChange={(val: string) => setKeywords(val)}
              />
            )}
          </Field>
        )}

        {/* Age limit (age_limit_days) */}
        {ruleType === "age_limit_days" && (
          <Field id="rule-days" label="Maximum age (days)">
            {(fieldProps) => (
              <InputNumeric
                {...fieldProps}
                value={days}
                min={1}
                onChange={(val) => setDays(typeof val === "number" ? val : parseInt(String(val), 10) || 365)}
              />
            )}
          </Field>
        )}

        {/* LLM policy + content source (llm_check) */}
        {ruleType === "llm_check" && (
          <>
            <Field id="rule-policy" label="Policy (plain English)">
              {(fieldProps) => (
                <Textarea
                  {...fieldProps}
                  value={policy}
                  placeholder="Describe the compliance requirement in plain English…"
                  onChange={(val: string) => setPolicy(val)}
                  nativeProps={{ rows: 4 }}
                />
              )}
            </Field>
            <Combobox
              id="rule-llm-content"
              label="Evaluate against"
              clearable={false}
              options={LLM_CONTENT_OPTIONS}
              value={LLM_CONTENT_OPTIONS.find((o) => o.value === llmContent) ?? LLM_CONTENT_OPTIONS[0]}
              onChange={(option) => option && setLlmContent(option.value as "summary" | "chunks")}
            />
          </>
        )}

      </FieldsContainer>
    </Modal>
  );
}
