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

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ScannerErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Scanner Error Boundary caught:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-8 bg-destructive/10 border border-destructive/20 rounded-xl space-y-4 text-center">
          <AlertCircle className="w-12 h-12 text-destructive" />
          <div className="space-y-2">
            <h3 className="text-xl font-bold">Something went wrong with the scanner</h3>
            <p className="text-muted-foreground text-sm max-w-md">
              The camera or scan processing encountered an unexpected error.
              {this.state.error && (
                <code className="block mt-2 p-2 bg-black/5 rounded text-xs">{this.state.error.message}</code>
              )}
            </p>
          </div>
          <Button onClick={this.handleReset} variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Reload Scanner
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
