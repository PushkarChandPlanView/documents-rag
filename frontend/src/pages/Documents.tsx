import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
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
import { useItemDetail } from "@/hooks/useDocuments";

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

export default function Documents() {
  const navigate = useNavigate();
  const { folderId, docId } = useParams<{ folderId?: string; docId?: string }>();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const { data: breadcrumb = [] } = useFolderBreadcrumb(folderId ?? "");
  const selectedTab = (searchParams.get("tab") as DetailTab) ?? "details";

  // On refresh: useItemDetail fetches from GET /documents/:id.
  // On normal click: query cache is pre-seeded so it resolves instantly.
  const { data: selectedItem } = useItemDetail(docId);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [addLinkOpen, setAddLinkOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState<ItemFiltersState>({
    fileTypeIds: new Set(),
    statuses: new Set(),
  });

  const docPath = (id: string) =>
    folderId ? `/folders/${folderId}/${id}` : `/documents/${id}`;

  const primeCache = (item: UnifiedItem) =>
    queryClient.setQueryData(["document", item.id], item);

  const handleSelect = (item: UnifiedItem) => {
    if (item.id === docId) {
      navigate(folderId ? `/folders/${folderId}` : "/documents", { replace: true });
    } else {
      primeCache(item);
      navigate(docPath(item.id), { replace: true });
    }
  };

  const handleChatOpen = (doc: DocumentItem) => {
    primeCache(doc);
    navigate(`${docPath(doc.id)}?tab=chat`, { replace: true });
  };

  const handleBreadcrumbNavigate = (id: string | null) => {
    navigate(id ? `/folders/${id}` : "/documents");
  };

  return (
    <>
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
            right={{ width: "medium", open: !!docId }}
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
                  selectedId={docId}
                  filters={filters}
                />
              </MiddleContent>
            </ContentLayout.Middle>

            <ContentLayout.Right label="Details">
              {selectedItem && (
                <DetailsPane
                  item={selectedItem}
                  activeTab={selectedTab}
                  onClose={() => navigate(folderId ? `/folders/${folderId}` : "/documents", { replace: true })}
                />
              )}
            </ContentLayout.Right>
          </ContentLayout>
        </LayoutArea>
      </PageWrapper>

      <FileUploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} folderId={folderId} />
      <CreateFolderDialog open={createFolderOpen} onClose={() => setCreateFolderOpen(false)} parentId={folderId} />
      <AddLinkDialog open={addLinkOpen} onClose={() => setAddLinkOpen(false)} folderId={folderId} />
    </>
  );
}
