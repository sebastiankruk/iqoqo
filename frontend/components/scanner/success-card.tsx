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
"use client";

import { CheckCircle2, ArrowRight, ScanLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export interface SuccessCardProps {
  title: string;
  message: string;
  onViewItem: () => void;
  onScanNext: () => void;
}

export function SuccessCard({ title, message, onViewItem, onScanNext }: SuccessCardProps) {
  return (
    <Card className="w-full max-w-sm animate-in fade-in zoom-in duration-300">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
          <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
        </div>
        <CardTitle className="text-xl">Successfully Added!</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">{message}</p>
      </CardHeader>

      <CardContent className="text-center">
        <div className="p-4 rounded-lg bg-accent/50 border border-border/50">
          <p className="font-semibold text-foreground italic">{title}</p>
        </div>
      </CardContent>

      <CardFooter className="flex flex-col gap-2">
        <Button onClick={onViewItem} className="w-full gap-2">
          View in Collection
          <ArrowRight className="h-4 w-4" />
        </Button>
        <Button onClick={onScanNext} variant="outline" className="w-full gap-2">
          <ScanLine className="h-4 w-4" />
          Scan Another
        </Button>
      </CardFooter>
    </Card>
  );
}
