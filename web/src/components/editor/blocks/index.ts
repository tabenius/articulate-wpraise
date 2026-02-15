import type { ComponentType } from "react";
import type { BlockProps } from "@/types/blocks";
import { ParagraphBlock } from "./paragraph-block";
import { HeadingBlock } from "./heading-block";
import { ImageBlock } from "./image-block";
import { ListBlock } from "./list-block";
import { QuoteBlock } from "./quote-block";
import { CodeBlock } from "./code-block";
import { ColumnsBlock } from "./columns-block";
import { GroupBlock } from "./group-block";
import { ButtonsBlock } from "./buttons-block";
import { SpacerBlock } from "./spacer-block";
import { SeparatorBlock } from "./separator-block";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const BLOCK_COMPONENTS: Record<string, ComponentType<BlockProps<any>>> = {
  "core/paragraph": ParagraphBlock,
  "core/heading": HeadingBlock,
  "core/image": ImageBlock,
  "core/list": ListBlock,
  "core/quote": QuoteBlock,
  "core/code": CodeBlock,
  "core/columns": ColumnsBlock,
  "core/column": GroupBlock,
  "core/group": GroupBlock,
  "core/buttons": ButtonsBlock,
  "core/spacer": SpacerBlock,
  "core/separator": SeparatorBlock,
};
