import { useEffect, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty } from "@planview/pv-uikit";
import { Cancel } from "@planview/pv-icons";
import { documentsApi } from "@/api/documents";
import type { DocumentItem } from "@/types";
import { IMAGE_MIMES } from "@/constants";

// ── constants ─────────────────────────────────────────────────────────────────

const OFFICE_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.ms-powerpoint",
]);

const DOCX_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
]);

const XLSX_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
]);

const TEXT_MIMES = new Set(["text/plain", "text/markdown", "text/csv"]);

// ── types ─────────────────────────────────────────────────────────────────────

interface SheetData {
  name: string;
  rows: (string | number | null)[][];
}

// ── styles ────────────────────────────────────────────────────────────────────

const Overlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: #fff;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 ${spacing.medium}px;
  height: 52px;
  flex-shrink: 0;
  background: #202124;
  border-bottom: 1px solid rgba(255,255,255,0.12);
`;

const DocName = styled.span`
  ${text.small};
  font-weight: 600;
  color: #e8eaed;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: calc(100% - 80px);
`;

const CloseBtn = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 50%;
  flex-shrink: 0;
  color: #e8eaed;
  &:hover { background: rgba(255,255,255,0.1); }
  svg { width: 20px; height: 20px; fill: currentColor; }
`;

const Body = styled.div`
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
`;

const PreviewFrame = styled.iframe`
  width: 100%;
  flex: 1;
  border: none;
  background: #fff;
  min-height: 0;
`;

const ImageBody = styled.div`
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #202124;
  padding: ${spacing.large}px;
`;

const PreviewImage = styled.img`
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
`;

const TextContent = styled.pre`
  ${text.small};
  white-space: pre-wrap;
  word-break: break-word;
  padding: ${spacing.medium}px ${spacing.large}px;
  flex: 1;
  margin: 0;
  background: #fff;
  font-family: monospace;
  line-height: 1.7;
  color: ${color.textPrimary};
  overflow: auto;
`;

const DocxWrapper = styled.div`
  flex: 1;
  overflow: auto;
  padding: ${spacing.large}px;
  background: #fff;
  color: ${color.textPrimary};
  line-height: 1.7;
  font-size: 0.9rem;

  h1, h2, h3, h4 { margin: 0.8em 0 0.4em; font-weight: 600; }
  p { margin: 0 0 0.6em; }
  ul, ol { padding-left: 1.5em; margin: 0 0 0.6em; }
  table { border-collapse: collapse; width: 100%; margin: 0.8em 0; }
  td, th { border: 1px solid ${color.borderLight}; padding: 4px 8px; }
  strong { font-weight: 600; }
  em { font-style: italic; }
`;

const XlsxWrapper = styled.div`
  flex: 1;
  overflow: auto;
  padding: ${spacing.medium}px;
  background: #fff;
`;

const SheetTitle = styled.h3`
  ${text.regularSemibold};
  color: ${color.textPrimary};
  margin: ${spacing.medium}px 0 ${spacing.xsmall}px;
  &:first-child { margin-top: 0; }
`;

const TableScroll = styled.div`
  overflow-x: auto;
  margin-bottom: ${spacing.large}px;
`;

const Table = styled.table`
  border-collapse: collapse;
  font-size: 0.8rem;
  white-space: nowrap;
`;

const Th = styled.th`
  padding: 4px 10px;
  background: ${color.backgroundNeutral50};
  border: 1px solid ${color.borderLight};
  font-weight: 600;
  color: ${color.textSecondary};
  text-align: left;
`;

const Td = styled.td`
  padding: 4px 10px;
  border: 1px solid ${color.borderLight};
  color: ${color.textPrimary};
`;

const Center = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: ${spacing.medium}px;
  flex: 1;
  ${text.small};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px;
`;

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  doc: DocumentItem;
  onClose: () => void;
}

export function PreviewPane({ doc, onClose }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [sheets, setSheets] = useState<SheetData[] | null>(null);
  const [docxHtml, setDocxHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mime = doc.mime_type ?? "";
  const isImage = IMAGE_MIMES.includes(mime);
  const isPdf = mime === "application/pdf";
  const isText = TEXT_MIMES.has(mime);
  const isOffice = OFFICE_MIMES.has(mime);
  const isXlsx = XLSX_MIMES.has(mime);
  const isDocx = DOCX_MIMES.has(mime);
  const isLink = mime === "text/html";

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  useEffect(() => {
    if (isLink || isOffice) { setLoading(false); return; }

    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);
    setBlobUrl(null);
    setTextContent(null);
    setSheets(null);
    setDocxHtml(null);

    documentsApi.getFile(doc.id)
      .then(async (blob) => {
        if (isDocx) {
          // @ts-ignore — mammoth installed in Docker build via package.json
          const mammoth = await import("mammoth") as any;
          const ab = await blob.arrayBuffer();
          const result = await mammoth.convertToHtml({ arrayBuffer: ab });
          setDocxHtml(result.value);
        } else if (isXlsx) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-ts-comment
          // @ts-ignore — xlsx installed in Docker build via package.json
          const XLSX = await import("xlsx") as any;
          const ab = await blob.arrayBuffer();
          const wb = XLSX.read(ab, { type: "array" });
          const parsed: SheetData[] = (wb.SheetNames as string[]).map((name: string) => {
            const ws = wb.Sheets[name];
            const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null }) as (string | number | null)[][];
            return { name, rows };
          });
          setSheets(parsed);
        } else if (isText) {
          setTextContent(await blob.text());
        } else {
          objectUrl = URL.createObjectURL(blob);
          setBlobUrl(objectUrl);
        }
      })
      .catch(() => setError("Could not load file preview."))
      .finally(() => setLoading(false));

    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [doc.id, mime]);

  const handleDownload = async () => {
    try {
      const blob = await documentsApi.getFile(doc.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.name ?? "file";
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* silently fail */ }
  };

  const renderBody = () => {
    if (isLink) return (
      <Center>
        <span>This document is a web link — no file to preview.</span>
        {doc.source_url && (
          <a href={doc.source_url} target="_blank" rel="noreferrer">
            <ButtonEmpty>Open source URL</ButtonEmpty>
          </a>
        )}
      </Center>
    );

    if (isOffice) return (
      <Center>
        <span>Browser preview is not available for this file type.</span>
        <ButtonEmpty onClick={handleDownload}>Download to open</ButtonEmpty>
      </Center>
    );

    if (loading) return <Center>Loading preview…</Center>;
    if (error) return <Center>{error}</Center>;

    if (isDocx && docxHtml !== null) return (
      <DocxWrapper dangerouslySetInnerHTML={{ __html: docxHtml }} />
    );

    if (isXlsx && sheets) return (
      <XlsxWrapper>
        {sheets.map((sheet) => (
          <div key={sheet.name}>
            <SheetTitle>{sheet.name}</SheetTitle>
            <TableScroll>
              <Table>
                <thead>
                  <tr>
                    {(sheet.rows[0] ?? []).map((cell, i) => (
                      <Th key={i}>{cell ?? ""}</Th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.slice(1).map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <Td key={ci}>{cell ?? ""}</Td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableScroll>
          </div>
        ))}
      </XlsxWrapper>
    );

    if (isText && textContent !== null) return <TextContent>{textContent}</TextContent>;

    if (isImage && blobUrl) return (
      <ImageBody>
        <PreviewImage src={blobUrl} alt={doc.name ?? "preview"} />
      </ImageBody>
    );

    if (isPdf && blobUrl) return <PreviewFrame src={blobUrl} title={doc.name ?? "PDF preview"} />;

    return (
      <Center>
        <span>Preview not available.</span>
        <ButtonEmpty onClick={handleDownload}>Download file</ButtonEmpty>
      </Center>
    );
  };

  return (
    <Overlay>
      <Header>
        <DocName>{doc.name}</DocName>
        <CloseBtn onClick={onClose} aria-label="Close preview"><Cancel /></CloseBtn>
      </Header>
      <Body>{renderBody()}</Body>
    </Overlay>
  );
}
