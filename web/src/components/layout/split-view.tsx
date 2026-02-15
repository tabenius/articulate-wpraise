"use client";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { GripVertical } from "lucide-react";

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
}

export function SplitView({ left, right }: SplitViewProps) {
  return (
    <PanelGroup direction="horizontal" className="h-full">
      <Panel defaultSize={40} minSize={25} maxSize={60}>
        <div className="h-full overflow-hidden">{left}</div>
      </Panel>

      <PanelResizeHandle className="w-2 bg-border hover:bg-primary/20 transition-colors flex items-center justify-center group">
        <GripVertical className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
      </PanelResizeHandle>

      <Panel defaultSize={60} minSize={30}>
        <div className="h-full overflow-hidden">{right}</div>
      </Panel>
    </PanelGroup>
  );
}
