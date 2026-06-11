import { useState } from "react";
import styled from "styled-components";
import { RulesManagement } from "@/components/compliance/RulesManagement";
import { useAuthStore } from "@/store/authStore";
import Layout from "@/components/layout/Layout";
import { ComplianceToolbar } from "@/components/compliance/toolbar";
import { useUpdateRule } from "@/hooks/useCompliance";

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
`;

export function Compliance() {
  const isAdmin = useAuthStore((s) => s.isAdmin);

  // Pending active-state changes: ruleId → desired is_active
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const [showCreate, setShowCreate] = useState(false);
  const { mutate: updateRule, isPending: saving } = useUpdateRule();

  const dirtyCount = Object.keys(pending).length;

  function handleApply() {
    const entries = Object.entries(pending);
    if (!entries.length) return;
    let remaining = entries.length;
    entries.forEach(([id, is_active]) => {
      updateRule(
        { id, data: { is_active } },
        { onSettled: () => { if (--remaining === 0) setPending({}); } }
      );
    });
  }

  return (
    
      <PageWrapper>
        <ComplianceToolbar
          isAdmin={isAdmin}
          dirtyCount={dirtyCount}
          saving={saving}
          onApply={handleApply}
          onReset={() => setPending({})}
          onAddRule={() => setShowCreate(true)}
        />
        <RulesManagement
          isAdmin={isAdmin}
          pending={pending}
          setPending={setPending}
          showCreate={showCreate}
          onCloseCreate={() => setShowCreate(false)}
        />
      </PageWrapper>
  );
}
