import { ComboboxOption } from "@planview/pv-uikit";
import { SOURCE_ICON, SOURCE_HEADER } from "./constants";
import { TextField, SelectField, TextAreaField } from "./FormFields";
import {
  FormHeader, FormHeaderIconBox, FormHeaderText, FormHeaderTitle, FormHeaderSub,
  FormGrid, FullWidth,
} from "./styled";
import type { Source } from "./types";

interface SourceFormProps {
  source: NonNullable<Source>;
  field: (key: string) => { value: string; onChange: (val: string) => void };
}

export const SourceForm = ({ source, field }: SourceFormProps) => {
  const header = (
    <FormHeader>
      <FormHeaderIconBox>{SOURCE_ICON[source]}</FormHeaderIconBox>
      <FormHeaderText>
        <FormHeaderTitle>{SOURCE_HEADER[source].title}</FormHeaderTitle>
        <FormHeaderSub>{SOURCE_HEADER[source].subtitle}</FormHeaderSub>
      </FormHeaderText>
    </FormHeader>
  );

  switch (source) {
    case "jira":
      return (
        <>
          {header}
          <FormGrid>
            <TextField label="Key *"     placeholder="e.g. SUP-1234"        {...field("key")}     />
            <TextField label="Project *" placeholder="e.g. customer-support" {...field("project")} />
            <SelectField label="Issue Type *" {...field("issueType")} options={[
              { value: "bug",   label: "Bug"   },
              { value: "task",  label: "Task"  },
              { value: "story", label: "Story" },
              { value: "epic",  label: "Epic"  },
            ] as ComboboxOption[]} />
            <SelectField label="Status" {...field("status")} options={[
              { value: "open",        label: "Open"        },
              { value: "in_progress", label: "In Progress" },
              { value: "done",        label: "Done"        },
              { value: "closed",      label: "Closed"      },
            ] as ComboboxOption[]} />
            <FullWidth><TextField label="Summary *" placeholder="e.g. API integration failing on production" {...field("summary")} /></FullWidth>
            <FullWidth><TextAreaField label="Description *" placeholder="Detailed issue description…" {...field("description")} /></FullWidth>
          </FormGrid>
        </>
      );
    case "confluence":
      return (
        <>
          {header}
          <FormGrid>
            <TextField label="Key *"   placeholder="e.g. CONF-42"    {...field("key")}    />
            <TextField label="Space *" placeholder="e.g. engineering" {...field("space")}  />
            <TextField label="Page ID" placeholder="e.g. 123456"      {...field("pageId")} />
            <FullWidth><TextField label="Title *" placeholder="e.g. API Design Guidelines" {...field("title")} /></FullWidth>
            <FullWidth><TextAreaField label="Content *" placeholder="Paste page content to parse and index…" {...field("content")} /></FullWidth>
          </FormGrid>
        </>
      );
    case "github":
      return (
        <>
          {header}
          <FormGrid>
            <TextField label="Key *"        placeholder="e.g. GH-88"   {...field("key")}     />
            <TextField label="Repository *" placeholder="e.g. org/repo" {...field("repo")}    />
            <TextField label="Issue ID"     placeholder="e.g. 42"       {...field("issueId")} />
            <FullWidth><TextField label="Title *" placeholder="e.g. Fix null pointer in auth flow" {...field("title")} /></FullWidth>
            <FullWidth><TextAreaField label="Content *" placeholder="Paste issue or PR body to parse and index…" {...field("content")} /></FullWidth>
          </FormGrid>
        </>
      );
    case "slack":
      return (
        <>
          {header}
          <FormGrid>
            <TextField label="Key *"     placeholder="e.g. SLK-7"       {...field("key")}     />
            <TextField label="Channel *" placeholder="e.g. #eng-alerts" {...field("channel")} />
            <TextField label="User"      placeholder="e.g. @john.doe"   {...field("user")}    />
            <FullWidth><TextAreaField label="Message Content *" placeholder="Paste the Slack message content to parse and index…" {...field("content")} /></FullWidth>
          </FormGrid>
        </>
      );
    case "link":
      return (
        <>
          {header}
          <FormGrid>
            <FullWidth><TextField label="URL *"   placeholder="https://…"        {...field("url")}   /></FullWidth>
            <FullWidth><TextField label="Title *" placeholder="e.g. API Docs v3" {...field("title")} /></FullWidth>
            <TextField label="Key" placeholder="e.g. LNK-1" {...field("key")} />
            <FullWidth><TextAreaField label="Description" placeholder="Optional description of this link…" {...field("description")} /></FullWidth>
          </FormGrid>
        </>
      );
  }
};
