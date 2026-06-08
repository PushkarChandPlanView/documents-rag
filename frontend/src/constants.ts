export const MIME_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
  "application/msword": "Word",
  "text/plain": "Text",
  "text/markdown": "Markdown",
  "text/csv": "CSV",
  "text/html": "Link",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
  "application/vnd.ms-excel": "Excel",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
  "application/vnd.ms-powerpoint": "PowerPoint",
  "image/jpeg": "Image",
  "image/jpg":  "Image",
  "image/png":  "PNG",
  "image/tiff": "TIFF",
  "image/bmp":  "BMP",
  "image/webp": "WebP",
  "image/gif":  "GIF",
};

export const IMAGE_MIMES = ["image/jpeg", "image/jpg", "image/png", "image/tiff", "image/bmp", "image/webp", "image/gif"];

export const FILE_TYPE_MIMES: Record<string, string[]> = {
  pdf: ["application/pdf"],
  word: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"],
  text: ["text/plain"],
  markdown: ["text/markdown"],
  csv: ["text/csv"],
  excel: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"],
  powerpoint: [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
  ],
  image: IMAGE_MIMES,
};