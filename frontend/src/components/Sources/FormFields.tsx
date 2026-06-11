import { Combobox, Field, Input, Textarea } from "@planview/pv-form";
import { ComboboxOption } from "@planview/pv-uikit";
import React from "react";

const fieldId = (label: string) => label.toLowerCase().replace(/[^a-z0-9]+/g, "-");

// ── TextField ─────────────────────────────────────────────────────────────────
type TFProps = { label: string; value: string; onChange: (v: string) => void; placeholder?: string };
export const TextField = ({ label, value, onChange, placeholder }: TFProps) => (
  <Field id={fieldId(label)} label={label}>
    {(fp) => <Input {...fp} value={value} onChange={(v) => onChange(v)} placeholder={placeholder} />}
  </Field>
);

// ── SelectField ───────────────────────────────────────────────────────────────
type SelectFieldProps = { label: string; value: string; onChange: (v: string) => void; options: ComboboxOption[] };
export const SelectField = ({ label, value, onChange, options }: SelectFieldProps) => {
  const selected = options.find((o) => o.value === value) ?? null;
  return (
    <Field id={fieldId(label)} label={label}>
      {(fp) => (
        <Combobox
          {...fp}
          value={selected}
          onChange={(opt: ComboboxOption | null) => onChange(String(opt?.value ?? ""))}
          options={options}
        />
      )}
    </Field>
  );
};

// ── TextAreaField ─────────────────────────────────────────────────────────────
type TextAreaProps = { label: string; value: string; onChange: (v: string) => void; placeholder?: string };
export const TextAreaField = ({ label, value, onChange, placeholder }: TextAreaProps) => (
  <Field id={fieldId(label)} label={label}>
    {(fp) => <Textarea {...fp} value={value} onChange={(v) => onChange(v)} placeholder={placeholder} />}
  </Field>
);
