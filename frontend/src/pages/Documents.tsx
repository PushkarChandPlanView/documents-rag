import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import styled from "styled-components";
import { ContentLayout } from "@planview/pv-uikit";
import Layout from "@/components/layout/Layout";
import { ItemList } from "@/components/documents/ItemList";
import { DetailsPane } from "@/components/documents/detailspane";
import { ItemFilters } from "@/components/documents/ItemFilters";
import { ItemToolbar } from "@/components/documents/ItemToolbar";
import { FileUploadDialog } from "@/components/documents/FileUploadDialog";
import { CreateFolderDialog } from "@/components/documents/CreateFolderDialog";
import { AddLinkDialog } from "@/components/documents/AddLinkDialog";
import type { ItemFiltersState } from "@/components/documents/ItemFilters";
import type { DetailTab } from "@/components/documents/detailspane";
import type { DocumentItem, UnifiedItem } from "@/types";
import { useFolderBreadcrumb } from "@/hooks/useFolders";

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
`;

const LayoutArea = styled.div`
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
`;

const MiddleContent = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
`;

type Selection = { item: UnifiedItem; tab: DetailTab } | null;

export default function Documents() {
  const navigate = useNavigate();
  const { folderId } = useParams<{ folderId?: string }>();
  const { data: breadcrumb = [] } = useFolderBreadcrumb(folderId ?? "");

  const [selection, setSelection] = useState<Selection>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [addLinkOpen, setAddLinkOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState<ItemFiltersState>({
    fileTypeIds: new Set(),
    statuses: new Set(),
  });

  const handleSelect = (item: UnifiedItem) => {
    setSelection((prev) => prev?.item.id === item.id ? null : { item, tab: "details" });
  };

  const handleChatOpen = (doc: DocumentItem) => {
    setSelection({ item: doc, tab: "chat" });
  };

  const handleBreadcrumbNavigate = (id: string | null) => {
    navigate(id ? `/folders/${id}` : "/");
  };

  return (
    <Layout>
      <PageWrapper>
        <ItemToolbar
          onToggleFilter={() => setFilterOpen((v) => !v)}
          onUpload={() => setUploadOpen(true)}
          onCreateFolder={() => setCreateFolderOpen(true)}
          onAddLink={() => setAddLinkOpen(true)}
          breadcrumb={folderId ? breadcrumb : undefined}
          onBreadcrumbNavigate={folderId ? handleBreadcrumbNavigate : undefined}
        />

        <LayoutArea>
          <ContentLayout
            left={{ width: "small", open: filterOpen }}
            right={{ width: "medium", open: !!selection }}
          >
            <ContentLayout.Left label="Filters">
              <ItemFilters value={filters} onChange={setFilters} />
            </ContentLayout.Left>

            <ContentLayout.Middle>
              <MiddleContent>
                <ItemList
                  parentId={folderId}
                  onSelect={handleSelect}
                  onChatOpen={handleChatOpen}
                  onFolderOpen={(id) => navigate(`/folders/${id}`)}
                  selectedId={selection?.item.id}
                  filters={filters}
                />
              </MiddleContent>
            </ContentLayout.Middle>

            <ContentLayout.Right label="Details">
              {selection && (
                <DetailsPane
                  item={selection.item}
                  activeTab={selection.tab}
                  onClose={() => setSelection(null)}
                />
              )}
            </ContentLayout.Right>
          </ContentLayout>
        </LayoutArea>
      </PageWrapper>

      <FileUploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} folderId={folderId} />
      <CreateFolderDialog open={createFolderOpen} onClose={() => setCreateFolderOpen(false)} parentId={folderId} />
      <AddLinkDialog open={addLinkOpen} onClose={() => setAddLinkOpen(false)} folderId={folderId} />
    </Layout>
  );
}
