// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

"use client";

import * as React from "react";
import { Printer, Download, QrCode } from "lucide-react";
import { toast } from "sonner";
import type { Item } from "@/types/frbr";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";

interface PrintQrCodeDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  item: Item;
}

/**
 * Dialog for generating, downloading, and printing a QR code physical tracking label.
 *
 * @param root0 - The props object
 * @param root0.isOpen - Whether the dialog is open
 * @param root0.onOpenChange - Callback called when open state changes
 * @param root0.item - The physical copy item to display
 * @returns {React.JSX.Element} The component
 */
export function PrintQrCodeDialog({ isOpen, onOpenChange, item }: PrintQrCodeDialogProps) {
  const [qrBlobUrl, setQrBlobUrl] = React.useState<string>("");
  const blobUrlRef = React.useRef<string>("");

  React.useEffect(() => {
    if (!isOpen) {
      if (blobUrlRef.current) {
        window.URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = "";
        setQrBlobUrl("");
      }
      return;
    }

    let active = true;
    const fetchQr = async () => {
      try {
        const res = await apiClient.get(`/qrcode/${item.id}?format=png`, {
          responseType: "blob",
        });
        if (active) {
          const url = window.URL.createObjectURL(res.data);
          blobUrlRef.current = url;
          setQrBlobUrl(url);
        }
      } catch {
        toast.error("Failed to load QR code image.");
      }
    };

    fetchQr();

    return () => {
      active = false;
    };
  }, [isOpen, item.id]);

  const title = item.work?.title || item.title || "Untitled";
  const authors = React.useMemo(() => item.work?.authors || [], [item.work?.authors]);
  const contentType = item.expression?.content_type || "Item";

  const handlePrint = React.useCallback(() => {
    if (!qrBlobUrl) {
      toast.error("QR Code is not loaded yet.");
      return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      toast.error("Popup blocked! Please allow popups to print.");
      return;
    }

    const authorsText = authors.length > 0 ? `by ${authors.join(", ")}` : "";

    printWindow.document.write(`
      <html>
        <head>
          <title>Print Label - ${title}</title>
          <style>
            @page {
              size: auto;
              margin: 0mm;
            }
            body {
              font-family: system-ui, -apple-system, sans-serif;
              margin: 0;
              padding: 20px;
              display: flex;
              justify-content: center;
              align-items: center;
              min-height: 100vh;
              background-color: white;
            }
            .label-container {
              border: 2px dashed #ccc;
              padding: 20px;
              border-radius: 8px;
              width: 260px;
              text-align: center;
              background: white;
            }
            .qr-image {
              width: 180px;
              height: 180px;
              margin: 0 auto 12px;
              display: block;
            }
            .title {
              font-size: 16px;
              font-weight: 700;
              margin: 0 0 4px 0;
              color: black;
              word-wrap: break-word;
            }
            .author {
              font-size: 13px;
              color: #444;
              margin: 0 0 10px 0;
              word-wrap: break-word;
            }
            .meta {
              font-size: 10px;
              color: #666;
              text-transform: uppercase;
              letter-spacing: 0.05em;
              font-weight: 600;
            }
            @media print {
              body {
                padding: 0;
              }
              .label-container {
                border: none;
              }
            }
          </style>
        </head>
        <body>
          <div class="label-container">
            <img class="qr-image" src="${qrBlobUrl}" alt="QR Code" />
            <div class="title">${title}</div>
            ${authorsText ? `<div class="author">${authorsText}</div>` : ""}
            <div class="meta">iqoqo ID: #${item.id} &bull; ${contentType}</div>
          </div>
          <script>
            window.onload = function() {
              window.print();
              setTimeout(function() { window.close(); }, 500);
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  }, [item.id, title, authors, contentType, qrBlobUrl]);

  const handleDownload = React.useCallback(() => {
    if (!qrBlobUrl) {
      toast.error("QR Code is not loaded yet.");
      return;
    }
    try {
      const link = document.createElement("a");
      link.href = qrBlobUrl;
      link.download = `iqoqo-qr-item-${item.id}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("QR Code image downloaded.");
    } catch {
      toast.error("Failed to download QR code image.");
    }
  }, [item.id, qrBlobUrl]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <QrCode className="h-5 w-5 text-primary" />
            Physical Copy Tracking Label
          </DialogTitle>
          <DialogDescription>
            Generate and print a QR code label to attach to your physical copy. Scan it anytime to view or track.
          </DialogDescription>
        </DialogHeader>

        {/* Preview Container */}
        <div className="flex flex-col items-center justify-center py-6">
          <span className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
            Physical Label Preview
          </span>
          <div className="flex w-[260px] flex-col items-center rounded-xl border border-border/80 bg-card p-6 shadow-md ring-1 ring-border/20 transition-all hover:shadow-lg dark:bg-zinc-950/40">
            {/* QR code representation */}
            <div className="relative mb-4 flex h-[180px] w-[180px] items-center justify-center overflow-hidden rounded-lg border border-border/50 bg-white p-2">
              {qrBlobUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={qrBlobUrl} alt="QR Code" className="h-full w-full object-contain" />
              ) : (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              )}
            </div>
            <div className="w-full text-center">
              <h4 className="line-clamp-2 text-sm font-bold text-foreground leading-tight">{title}</h4>
              {authors.length > 0 && (
                <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">by {authors.join(", ")}</p>
              )}
              <div className="mt-3 flex items-center justify-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-muted-foreground/80">
                <span>iqoqo ID: #{item.id}</span>
                <span>&bull;</span>
                <span>{contentType}</span>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="grid grid-cols-2 gap-2 sm:justify-start">
          <Button variant="outline" className="flex items-center gap-2" onClick={handleDownload} disabled={!qrBlobUrl}>
            <Download className="h-4 w-4" />
            Download PNG
          </Button>
          <Button className="flex items-center gap-2" onClick={handlePrint} disabled={!qrBlobUrl}>
            <Printer className="h-4 w-4" />
            Print Label
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
