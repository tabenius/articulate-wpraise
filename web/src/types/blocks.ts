export interface Block {
  name: string;
  clientId: string;
  attributes: Record<string, unknown>;
  innerBlocks: Block[];
}

export interface ParagraphAttributes {
  content: string;
  align?: string;
  className?: string;
  dropCap?: boolean;
}

export interface HeadingAttributes {
  content: string;
  level: 1 | 2 | 3 | 4 | 5 | 6;
  textAlign?: string;
  className?: string;
}

export interface ImageAttributes {
  url: string;
  alt: string;
  caption?: string;
  width?: number;
  height?: number;
  className?: string;
  sizeSlug?: string;
}

export interface ListAttributes {
  ordered: boolean;
  values: string;
  className?: string;
}

export interface QuoteAttributes {
  value: string;
  citation?: string;
  className?: string;
}

export interface CodeAttributes {
  content: string;
  className?: string;
}

export interface ColumnsAttributes {
  verticalAlignment?: string;
  className?: string;
}

export interface ColumnAttributes {
  width?: string;
  verticalAlignment?: string;
  className?: string;
}

export interface GroupAttributes {
  tagName?: string;
  className?: string;
}

export interface ButtonAttributes {
  text: string;
  url?: string;
  className?: string;
}

export interface SpacerAttributes {
  height: string;
  className?: string;
}

export interface SeparatorAttributes {
  className?: string;
  opacity?: string;
}

export interface BlockProps<T = Record<string, unknown>> {
  block: Block;
  attributes: T;
  isSelected: boolean;
  onUpdate: (attributes: Partial<T>) => void;
}

export const BLOCK_LABELS: Record<string, string> = {
  "core/paragraph": "Paragraph",
  "core/heading": "Heading",
  "core/image": "Image",
  "core/list": "List",
  "core/quote": "Quote",
  "core/code": "Code",
  "core/columns": "Columns",
  "core/column": "Column",
  "core/group": "Group",
  "core/buttons": "Buttons",
  "core/button": "Button",
  "core/spacer": "Spacer",
  "core/separator": "Separator",
  "core/table": "Table",
  "core/embed": "Embed",
  "core/html": "HTML",
  "core/freeform": "Classic",
};
