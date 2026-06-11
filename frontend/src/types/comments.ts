// Comment domain types — mirror the backend Pydantic schemas exactly

export interface CommentAuthor {
  id: string;
  name: string;
  avatar?: string | null;
}

export interface CommentItem {
  id: string;
  document_id: string;
  parent_id: string | null;
  content: string;
  author: CommentAuthor;
  created_at: string;
  updated_at: string;
  like_count: number;
  liked_by_me: boolean;
  replies: CommentItem[];
}

export interface PaginatedComments {
  items: CommentItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface CommentCreate {
  document_id: string;
  content: string;
  parent_id?: string;
}

export interface CommentUpdate {
  content: string;
}
