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
/**
 * The scan page for capturing barcodes, covers, and manual entry.
 *
 * @module app/scan/page
 */
"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import { DisambiguationSheet } from "@/components/scanner/disambiguation-sheet";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import type { ManualEntryData } from "@/components/scanner/manual-entry-form";
import { ScannerErrorBoundary } from "@/components/scanner/error-boundary";
import { useAddManualItem, queryKeys, useAppConfig } from "@/lib/api/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Search, Loader2, Radio, Library, BookmarkCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useBatchMode, BatchScanToggle } from "@/components/scanner/batch-scan-toggle";
import { triggerScanHaptic, triggerErrorHaptic } from "@/lib/capacitor/haptics";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta, ScanFormat, ApiResponse } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";
import { mapFormatToApi } from "@/lib/media";
import {
  findOfflineDuplicate,
  enqueueOfflineManualEntry,
  flushOfflineManualQueue,
} from "@/lib/capacitor/offline-cache";

/**
 * The scan page component for scanning barcodes and manual entry.
 *
 * @returns {JSX.Element} The ScanPage component
 */
export default function ScanPage() {
  const [result, setResult] = useState<{ isbn: string; meta: IsbnMeta } | null>(null);
  const [candidates, setCandidates] = useState<{ isbn: string; items: IsbnMeta[] } | null>(null);
  const [showManual, setShowManual] = useState(false);
  const [initialIdentifier, setInitialIdentifier] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [scannerActive, setScannerActive] = useState(false);
  const [scannerTab, setScannerTab] = useState<"barcode" | "cover" | "manual">("barcode");
  const [activeFormat, setActiveFormat] = useState<ScanFormat>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      const savedFormat = window.localStorage.getItem("iqoqo_scanner_media_type");
      if (savedFormat) return savedFormat as ScanFormat;
    }
    return "book";
  });
  const [policy, setPolicy] = useState<"inventory" | "wishlist" | "catalog">(
    (): "inventory" | "wishlist" | "catalog" => {
      if (typeof window !== "undefined" && window.localStorage) {
        const savedPolicy = window.localStorage.getItem("iqoqo_scanner_policy");
        if (savedPolicy === "inventory" || savedPolicy === "wishlist" || savedPolicy === "catalog") {
          return savedPolicy;
        }
      }
      return "inventory";
    }
  );
  const [snappedCover, setSnappedCover] = useState<File | null>(null);
  const [hasTorch, setHasTorch] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [autoStart, setAutoStart] = useState(() => {
    if (typeof window !== "undefined" && window.sessionStorage) {
      if (window.sessionStorage.getItem("iqoqo_auto_start_camera") === "true") {
        window.sessionStorage.removeItem("iqoqo_auto_start_camera");
        return true;
      }
    }
    return false;
  });

  const inFlightBarcodesRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("iqoqo_scanner_media_type", activeFormat);
    }
  }, [activeFormat]);

  useEffect(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("iqoqo_scanner_policy", policy);
    }
  }, [policy]);

  const addManualMutation = useAddManualItem();
  const router = useRouter();
  const t = useTranslations("scanner");
  const queryClient = useQueryClient();
  const { data: config } = useAppConfig();
  const isFederationHead = config?.federation_head_mode === true;

  const { isBatchMode, setBatchMode, scannedQueue, isCooldownActive, recordScan, clearQueue } = useBatchMode();

  const [quickQuery, setQuickQuery] = useState("");
  const [isQuickSearching, setIsQuickSearching] = useState(false);

  // Auto-flush pending offline manual entries when back online
  useEffect(() => {
    const handleSync = async () => {
      try {
        const res = await flushOfflineManualQueue(async payload => {
          return await apiClient.post("/items/manual", payload);
        });
        if (res.synced > 0) {
          toast.success(`Synced ${res.synced} offline manual item${res.synced > 1 ? "s" : ""} to your library!`);
          queryClient.invalidateQueries({ queryKey: queryKeys.itemsRoot });
        }
      } catch {
        // Ignore background sync errors
      }
    };

    window.addEventListener("online", handleSync);
    if (typeof navigator !== "undefined" && navigator.onLine) {
      handleSync();
    }
    return () => {
      window.removeEventListener("online", handleSync);
    };
  }, [queryClient]);

  const formatToApiParam = (fmt?: string): string => {
    if (fmt === "movie" || fmt === "video") return "movie";
    if (fmt === "board_game" || fmt === "boardgame") return "board_game";
    if (fmt === "puzzle") return "puzzle";
    if (fmt === "music" || fmt === "audio") return "music";
    if (fmt === "lego") return "lego";
    if (fmt === "book") return "book";
    return "";
  };

  const handleFound = useCallback(
    async (isbn: string, meta: IsbnMeta) => {
      // Prefer the backend-normalized identifier/barcode if available
      const canonicalId = meta.identifier || meta.barcode || meta.isbn || isbn;

      // Continuous batch mode handling: auto-adds item, toasts, and keeps scanner active
      if (isBatchMode) {
        if (inFlightBarcodesRef.current.has(canonicalId) || isCooldownActive(canonicalId)) {
          return;
        }
        inFlightBarcodesRef.current.add(canonicalId);

        // Single tactile scan confirmation on native mobile
        await triggerScanHaptic();

        if (meta.candidates && meta.candidates.length > 1) {
          inFlightBarcodesRef.current.delete(canonicalId);
          setCandidates({ isbn: canonicalId, items: meta.candidates });
          return;
        }

        try {
          const payloadCollectionStatus = policy === "wishlist" ? "wish_list" : "available";
          const res = await apiClient.post<
            ApiResponse<{ item_id?: number | null; intent_id?: number; manifestation_id: number; action?: string }>
          >("/scan", {
            barcode: canonicalId,
            manifestation_id: meta.manifestation_id,
            format: mapFormatToApi(activeFormat),
            collection_status: payloadCollectionStatus,
            policy,
            meta: meta.data_source ? meta : undefined,
          });

          if (!res.data?.success) {
            throw new Error((res.data as unknown as { error?: string })?.error || "Failed to add item in batch mode");
          }

          const itemTitle = meta.title || meta.Title || "Scanned item";
          const authors = meta.authors || meta.Authors;
          const normalizedAuthors = Array.isArray(authors)
            ? authors.map((a: unknown) =>
                a && typeof a === "object" && "name" in a ? (a as { name: string }).name : String(a)
              )
            : undefined;

          recordScan(canonicalId, {
            id: res.data?.data?.item_id || undefined,
            title: itemTitle,
            authors: normalizedAuthors,
          });

          queryClient.invalidateQueries({ queryKey: queryKeys.items() });
          queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
          queryClient.invalidateQueries({ queryKey: ["works", "shelf"] });
          queryClient.invalidateQueries({ queryKey: ["expressions", "shelf"] });

          toast.success(t("batchMode.itemAddedToast", { title: itemTitle }));
          setAutoStart(true);
          return;
        } catch (err) {
          await triggerErrorHaptic();
          toast.error((err as Error).message || "Failed to add item in batch mode");
          return;
        } finally {
          inFlightBarcodesRef.current.delete(canonicalId);
        }
      }

      // Single scan mode
      await triggerScanHaptic();
      if (meta.candidates && meta.candidates.length > 1) {
        setCandidates({ isbn: canonicalId, items: meta.candidates });
      } else {
        setResult({ isbn: canonicalId, meta });
      }
    },
    [isBatchMode, isCooldownActive, policy, activeFormat, recordScan, queryClient, t]
  );

  const handleQuickLookup = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = quickQuery.trim();
    if (!query) return;

    setIsQuickSearching(true);
    try {
      const { apiFetch } = await import("@/lib/api/client");
      const formatParam = formatToApiParam(activeFormat);
      const url = formatParam
        ? `/lookup/${encodeURIComponent(query)}?format=${formatParam}`
        : `/lookup/${encodeURIComponent(query)}`;
      const data = await apiFetch<IsbnMeta>(url);
      setQuickQuery("");
      await handleFound(query, data);
    } catch {
      // Check offline cache when lookup fails or network offline
      const offlineMatch = await findOfflineDuplicate(query);
      if (offlineMatch) {
        toast.info(offlineMatch.matchType === "collection" ? t("offlineMatchCollection") : t("offlineMatchWishlist"));
      } else {
        toast.info(t("bottomSheet.lookupFailed"));
      }
      handleShowManualForm(query);
    } finally {
      setIsQuickSearching(false);
    }
  };

  const handleScanAnother = useCallback(() => {
    setResult(null);
    setCandidates(null);
    setAutoStart(true);
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
    setCandidates(null);
    setAutoStart(false);
  }, []);

  const handleExtractComplete = useCallback((data: { Title?: string; Authors?: string[] }, file?: File) => {
    setTitle(data.Title || "");
    setAuthor(data.Authors?.join(", ") || "");
    if (file) setSnappedCover(file);
    setInitialIdentifier("");
    setShowManual(true);
    toast.success("Cover metadata extracted! Please review.");
  }, []);

  const handleShowManualForm = useCallback((isbn?: string) => {
    setInitialIdentifier(isbn || "");
    setShowManual(true);
  }, []);

  const handleExtractionFailure = useCallback(
    (ean: string) => {
      handleShowManualForm(ean);
      toast.info("Switching to manual entry...");
    },
    [handleShowManualForm]
  );

  const handleManualSubmit = async (data: ManualEntryData) => {
    const authors = data.authors
      ? data.authors
          .split(",")
          .map(a => a.trim())
          .filter(Boolean)
      : ["Unknown"];

    let explicitDate = data.year || undefined;
    if (explicitDate && /^\d{4}$/.test(explicitDate)) {
      explicitDate = `${explicitDate}-01-01`;
    }

    const apiFormat = mapFormatToApi(data.format);

    const payload = {
      Title: data.title || "Unknown",
      Authors: authors.length > 0 ? authors : ["Unknown"],
      Format: apiFormat,
      ISBN: data.identifier || undefined,
      PublicationDate: explicitDate,
      Publisher: data.publisher || undefined,
    };

    const isCurrentlyOffline = typeof navigator !== "undefined" && !navigator.onLine;
    if (isCurrentlyOffline) {
      await enqueueOfflineManualEntry(payload);
      toast.success(`"${payload.Title}" saved locally! Will sync when back online.`);
      setShowManual(false);
      return;
    }

    addManualMutation.mutate(payload, {
      onSuccess: async response => {
        const item = response.data;
        const coverToUpload = data.coverFile || snappedCover;

        if (item && coverToUpload && item.manifestation_id) {
          const coverFormData = new FormData();
          coverFormData.append("cover", coverToUpload);
          const isSnapped = coverToUpload === snappedCover;
          coverFormData.append("source", isSnapped ? "scanner_camera" : "user_upload");
          try {
            await apiClient.post(`/manifestations/${item.manifestation_id}/cover`, coverFormData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            toast.success(`"${payload.Title}" added with your custom cover!`);
          } catch (e) {
            const errMsg = (e as Error)?.message || "Cover upload failed";
            console.error("Failed to upload cover:", e);
            toast.error(`"${payload.Title}" added, but cover upload failed: ${errMsg}`);
          }
        } else {
          toast.success(`"${payload.Title}" added to your library!`);
        }

        if (response.data?.item_id) {
          router.push(`/item/${response.data.item_id}`);
        }
      },
      onError: async () => {
        // If network error occurred during submission, save to offline manual queue
        await enqueueOfflineManualEntry(payload);
        toast.info(`Network unreachable: "${payload.Title}" queued locally for sync.`);
        setShowManual(false);
      },
    });
  };

  const handleToggleTorch = useCallback(() => {
    setTorchOn(prev => !prev);
  }, []);

  if (isFederationHead) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 bg-background">
        <div
          data-testid="federation-head-scan-notice"
          className="max-w-md w-full p-6 rounded-2xl border border-border/80 bg-card shadow-lg text-center space-y-5"
        >
          <div className="h-12 w-12 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center mx-auto text-accent">
            <Radio className="h-6 w-6 animate-pulse" />
          </div>
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-accent/15 text-accent border border-accent/30">
              {t("federationHub.badge")}
            </span>
            <h2 className="text-xl font-bold tracking-tight text-foreground">{t("federationHub.title")}</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">{t("federationHub.description")}</p>
          </div>
          <p className="text-xs text-muted-foreground/80 italic">{t("federationHub.wishlistHint")}</p>
          <div className="flex flex-col gap-2.5 pt-2">
            <Button asChild size="default" className="w-full bg-accent text-accent-foreground font-semibold">
              <Link href="/collection" className="flex items-center justify-center gap-2">
                <Library className="h-4 w-4" />
                {t("federationHub.exploreCatalog")}
              </Link>
            </Button>
            <Button asChild variant="outline" size="default" className="w-full">
              <Link href="/federation/directory" className="flex items-center justify-center gap-2">
                <Radio className="h-4 w-4" />
                {t("federationHub.viewDirectory")}
              </Link>
            </Button>
            <Button asChild variant="ghost" size="sm" className="w-full text-muted-foreground">
              <Link href="/wishlist" className="flex items-center justify-center gap-2">
                <BookmarkCheck className="h-4 w-4" />
                Wishlist
              </Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ScannerErrorBoundary>
      <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E"
          suppressHydrationWarning
          className={`absolute inset-0 z-0 h-full w-full object-cover transition-opacity duration-300 ${
            scannerActive ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
        />

        <TopBar
          currentFormat={activeFormat}
          setFormat={f => setActiveFormat(f as ScanFormat)}
          currentPolicy={policy}
          setPolicy={setPolicy}
          hasFlash={hasTorch}
          isFlashOn={torchOn}
          onToggleFlash={handleToggleTorch}
        >
          {!result && !showManual && (
            <div className="flex items-center gap-2">
              <form
                onSubmit={handleQuickLookup}
                className="flex flex-1 min-w-0 h-9 items-center rounded-xl bg-background/80 backdrop-blur-md border border-border/40 shadow-sm px-3 focus-within:border-primary/60"
              >
                <Search className="h-4 w-4 text-muted-foreground mr-2 shrink-0" />
                <input
                  data-testid="unified-lookup-input"
                  type="text"
                  value={quickQuery}
                  onChange={e => setQuickQuery(e.target.value)}
                  placeholder={t("unifiedLookup.placeholder")}
                  className="flex-1 min-w-0 bg-transparent text-xs text-foreground placeholder:text-muted-foreground/70 focus:outline-none"
                />
                <Button
                  data-testid="unified-lookup-submit"
                  type="button"
                  onClick={handleQuickLookup}
                  size="sm"
                  disabled={!quickQuery.trim() || isQuickSearching}
                  className="h-7 px-2.5 text-xs ml-1 shrink-0 rounded-lg"
                >
                  {isQuickSearching ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    t("unifiedLookup.searchButton")
                  )}
                </Button>
              </form>

              <BatchScanToggle
                enabled={isBatchMode}
                onToggle={setBatchMode}
                queueCount={scannedQueue.length}
                recentItems={scannedQueue}
                onClearQueue={clearQueue}
                className="shrink-0"
              />
            </div>
          )}
        </TopBar>

        {!result && !showManual && scannerTab === "barcode" && (
          <Viewfinder isScanning={scannerActive} format={activeFormat} />
        )}

        {!result && !showManual && (
          <BottomSheet
            videoRef={videoRef}
            onFound={handleFound}
            onScannerStateChange={setScannerActive}
            onTabChange={setScannerTab}
            onExtractComplete={handleExtractComplete}
            onExtractionFailure={handleExtractionFailure}
            onShowManualForm={handleShowManualForm}
            format={activeFormat}
            torchOn={torchOn}
            onTorchCapabilityFound={setHasTorch}
            autoStart={autoStart}
          />
        )}
        {result && (
          <SuccessCard
            isbn={result.isbn}
            meta={result.meta}
            policy={policy}
            onDismiss={handleDismiss}
            onScanAnother={handleScanAnother}
            snappedCover={snappedCover}
            onShowManualForm={handleShowManualForm}
          />
        )}

        {candidates && (
          <DisambiguationSheet
            candidates={candidates.items}
            onSelect={choice => {
              setCandidates(null);
              // Derive a stable identifier from the selected candidate
              const candidateObj = (choice || {}) as unknown as Record<string, unknown>;
              const selectedIdentifier =
                (typeof candidateObj.identifier === "string" && candidateObj.identifier) ||
                (typeof candidateObj.barcode === "string" && candidateObj.barcode) ||
                (typeof candidateObj.isbn === "string" && candidateObj.isbn) ||
                candidates.isbn;

              const metaObj: IsbnMeta = {
                ...choice,
                data_source: choice.data_source || "search",
              };

              setResult({ isbn: selectedIdentifier, meta: metaObj });
            }}
            onDismiss={handleDismiss}
          />
        )}

        {showManual && (
          <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
            <ManualEntryForm
              onSubmit={handleManualSubmit}
              onCancel={() => setShowManual(false)}
              initialTitle={title}
              initialAuthors={author}
              initialFormat={activeFormat}
              initialIdentifier={initialIdentifier}
              initialCoverFile={snappedCover}
            />
          </div>
        )}
      </div>
    </ScannerErrorBoundary>
  );
}
