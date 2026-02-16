"use client";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
}

export function SplitView({ left, right }: SplitViewProps) {
  return (
    <PanelGroup direction="horizontal" className="h-full">
      <Panel
        defaultSize={40}
        minSize={25}
        maxSize={60}
        id="chat-panel"
        order={1}
      >
        {left}
      </Panel>

      <PanelResizeHandle className="w-1 bg-border hover:bg-primary/20 transition-colors cursor-col-resize group">
        <div className="w-full h-full flex items-center justify-center">
          <div className="w-0.5 h-8 bg-border group-hover:bg-primary/40 rounded-full transition-colors" />
        </div>
      </PanelResizeHandle>

      <Panel
        defaultSize={60}
        minSize={40}
        id="editor-panel"
        order={2}
      >
        {right}
      </Panel>
    </PanelGroup>
  );
}
