'use client';

import { Button } from '@/components/ui/button';
import { RotateCw, FlipHorizontal, FlipVertical, Disc3, Book, Scaling } from 'lucide-react';

interface EditorToolbarProps {
  aspect: number | undefined;
  setAspect: (aspect: number | undefined) => void;
  setRotation: React.Dispatch<React.SetStateAction<number>>;
  flipH: boolean;
  setFlipH: (val: boolean) => void;
  flipV: boolean;
  setFlipV: (val: boolean) => void;
}

/**
 * Toolbar component for adjusting aspects, rotation, and flipping of the cover.
 *
 * @param props - Editor configuration states.
 * @returns The rendered toolbar.
 */
export function EditorToolbar({ aspect, setAspect, setRotation, flipH, setFlipH, flipV, setFlipV }: EditorToolbarProps) {
  return (
    <div className="flex items-center space-x-2 p-2 border-b bg-background">
      <div className="flex items-center space-x-1 pr-2">
        <Button variant={aspect === 1 ? "secondary" : "ghost"} size="sm" onClick={() => setAspect(1)}>
          <Disc3 className="mr-2 w-4 h-4" /> 1:1
        </Button>
        <Button variant={aspect === 2/3 ? "secondary" : "ghost"} size="sm" onClick={() => setAspect(2/3)}>
          <Book className="mr-2 w-4 h-4" /> 2:3
        </Button>
        <Button variant={aspect === undefined ? "secondary" : "ghost"} size="sm" onClick={() => setAspect(undefined)}>
          <Scaling className="mr-2 w-4 h-4" /> Freeform
        </Button>
      </div>

      <div className="w-px h-6 bg-border mx-2" />

      <div className="flex items-center space-x-1 pl-2">
        <Button variant="ghost" size="icon" onClick={() => setRotation((r) => r + 90)} title="Rotate 90°">
          <RotateCw className="h-4 w-4" />
        </Button>
        <Button variant={flipH ? "secondary" : "ghost"} size="icon" onClick={() => setFlipH(!flipH)} title="Flip Horizontal">
          <FlipHorizontal className="h-4 w-4" />
        </Button>
        <Button variant={flipV ? "secondary" : "ghost"} size="icon" onClick={() => setFlipV(!flipV)} title="Flip Vertical">
          <FlipVertical className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
