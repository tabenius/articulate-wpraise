"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { useEffect } from "react";

interface RichTextEditorProps {
  content: string;
  placeholder?: string;
  onChange: (html: string) => void;
  isSelected: boolean;
  className?: string;
}

export function RichTextEditor({
  content,
  placeholder = "Start typing...",
  onChange,
  isSelected,
  className = "",
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable features we don't need for simple text blocks
        heading: false, // Heading blocks have their own component
        codeBlock: false, // Code blocks have their own component
        blockquote: false, // Quote blocks have their own component
        bulletList: false, // List blocks have their own component
        orderedList: false,
        horizontalRule: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    editorProps: {
      attributes: {
        class: `prose prose-slate max-w-none focus:outline-none ${className}`,
        spellcheck: "true",
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      onChange(html);
    },
    // Auto-focus when selected
    autofocus: isSelected,
  });

  // Update content if it changes externally (e.g., from AI)
  useEffect(() => {
    if (!editor) return;

    const currentContent = editor.getHTML();
    // Only update if content actually changed to avoid cursor jumps
    if (content !== currentContent && content !== editor.getText()) {
      editor.commands.setContent(content, false);
    }
  }, [content, editor]);

  // Handle selection state
  useEffect(() => {
    if (!editor) return;

    if (isSelected && !editor.isFocused) {
      editor.commands.focus("end");
    }
  }, [isSelected, editor]);

  if (!editor) {
    return <div className="min-h-[1.5em]">Loading...</div>;
  }

  return (
    <div
      className={`min-h-[1.5em] ${
        isSelected
          ? "ring-2 ring-primary/20 rounded-sm px-2 py-1"
          : "px-2 py-1"
      }`}
    >
      <EditorContent editor={editor} />
    </div>
  );
}
