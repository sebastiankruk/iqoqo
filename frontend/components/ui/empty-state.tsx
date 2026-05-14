// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//

import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

interface EmptyStateProps {
  /** Title of the empty state */
  title: string;
  /** Optional description text */
  description?: string;
  /** Optional Lucide icon to display */
  icon?: LucideIcon;
  /** Optional action button or node */
  action?: React.ReactNode;
  /** Optional additional class names for the container */
  className?: string;
}

/**
 * Reusable empty state component with a dashed border card.
 * @param root0 - The component props.
 * @param root0.title - Title of the empty state.
 * @param root0.description - Optional description text.
 * @param root0.icon - Optional Lucide icon to display.
 * @param root0.action - Optional action button or node.
 * @param root0.className - Optional additional class names for the container.
 * @returns The rendered empty state component.
 */
export function EmptyState({ title, description, icon: Icon, action, className }: EmptyStateProps) {
  return (
    <Card
      className={cn("flex flex-col items-center justify-center p-12 text-center border-dashed bg-muted/20", className)}
    >
      {Icon && <Icon className="w-12 h-12 mb-4 text-muted-foreground/40" strokeWidth={1.5} />}
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      {description && <p className="mt-2 text-sm text-muted-foreground max-w-xs mx-auto">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </Card>
  );
}
