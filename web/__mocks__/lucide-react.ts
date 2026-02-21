// Mock lucide-react icons
import React from 'react';

const createIcon = (displayName: string) => {
  const Icon = (props: any) => React.createElement('svg', { 'data-testid': displayName, ...props });
  Icon.displayName = displayName;
  return Icon;
};

export const Activity = createIcon('Activity');
export const TrendingUp = createIcon('TrendingUp');
export const Clock = createIcon('Clock');
export const AlertCircle = createIcon('AlertCircle');
export const Zap = createIcon('Zap');
export const CheckCircle2 = createIcon('CheckCircle2');
export const Image = createIcon('Image');
export const Upload = createIcon('Upload');
export const Download = createIcon('Download');
export const ArrowRight = createIcon('ArrowRight');
export const XCircle = createIcon('XCircle');
export const Loader2 = createIcon('Loader2');
export const FileArchive = createIcon('FileArchive');
export const Rocket = createIcon('Rocket');
export const Settings2 = createIcon('Settings2');
export const FileCode = createIcon('FileCode');
export const ChevronUp = createIcon('ChevronUp');
export const ChevronDown = createIcon('ChevronDown');
