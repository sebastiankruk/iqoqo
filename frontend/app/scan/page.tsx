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

import { useState, useCallback, useRef, useEffect, useSyncExternalStore } from "react";

const _subscribeNoop = () => () => {};
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import { DisambiguationSheet } from "@/components/scanner/disambiguation-sheet";
import { SerialDisambiguationModal } from "@/components/scanner/serial-disambiguation-modal";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import type { ManualEntryData } from "@/components/scanner/manual-entry-form";
import { ScannerErrorBoundary } from "@/components/scanner/error-boundary";
import { useAddManualItem, queryKeys, useAppConfig } from "@/lib/api/hooks";
import { COVER_JPEG_QUALITY, COVER_MAX_DIMENSION, resizeImageFile } from "@/lib/image-resize";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Search, Loader2, Radio, Library, BookmarkCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useBatchMode, BatchScanToggle } from "@/components/scanner/batch-scan-toggle";
import { triggerScanHaptic, triggerErrorHaptic } from "@/lib/capacitor/haptics";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import axios from "axios";
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
  const [serialDisambiguation, setSerialDisambiguation] = useState<IsbnMeta | null>(null);
  const clientSearch = useSyncExternalStore(
    _subscribeNoop,
    () => (typeof window !== "undefined" ? window.location.search : ""),
    () => ""
  );
  const clientSavedFormat = useSyncExternalStore(
    _subscribeNoop,
    () =>
      typeof window !== "undefined" && window.localStorage
        ? window.localStorage.getItem("iqoqo_scanner_media_type")
        : null,
    () => null
  );
  const clientSavedPolicy = useSyncExternalStore(
    _subscribeNoop,
    () =>
      typeof window !== "undefined" && window.localStorage ? window.localStorage.getItem("iqoqo_scanner_policy") : null,
    () => null
  );

  const searchParamsSnapshot = new URLSearchParams(clientSearch);
  const urlManual = searchParamsSnapshot.get("manual") === "1";
  const urlIssn = searchParamsSnapshot.get("issn") || "";
  const urlTitle = searchParamsSnapshot.get("title") || "";
  const urlPublisher = searchParamsSnapshot.get("publisher") || "";
  const urlFormat = searchParamsSnapshot.get("format");
  const urlPolicy = searchParamsSnapshot.get("policy");

  const [showManualOverride, setShowManual] = useState<boolean | null>(null);
  const [initialIdentifierOverride, setInitialIdentifier] = useState<string | null>(null);
  const [titleOverride, setTitle] = useState<string | null>(null);
  const [author, setAuthor] = useState("");
  const [serialDefaultsOverride, setSerialDefaults] = useState<{
    publisher?: string;
    year?: string;
    issn?: string;
    issueNumber?: string;
    cumulativeIssueNumber?: string;
    publicationMonth?: string;
    eanAddon?: string;
    coverHeadline?: string;
  } | null>(null);
  const [scannerActive, setScannerActive] = useState(false);
  const [scannerTab, setScannerTab] = useState<"barcode" | "cover">("barcode");
  const [activeFormatOverride, setActiveFormat] = useState<ScanFormat | null>(null);
  const [policyOverride, setPolicy] = useState<"inventory" | "wishlist" | "catalog" | null>(null);
  const [snappedCover, setSnappedCover] = useState<File | null>(null);
  const [hasTorch, setHasTorch] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [autoStart, setAutoStart] = useState(false);

  const showManual = showManualOverride ?? urlManual;
  const initialIdentifier = initialIdentifierOverride ?? urlIssn;
  const title = titleOverride ?? urlTitle;
  const serialDefaults =
    serialDefaultsOverride ?? (urlPublisher || urlIssn ? { publisher: urlPublisher, issn: urlIssn } : {});
  const activeFormat: ScanFormat = activeFormatOverride ?? ((urlFormat || clientSavedFormat || "book") as ScanFormat);
  const policy: "inventory" | "wishlist" | "catalog" =
    policyOverride ??
    (urlPolicy === "inventory" || urlPolicy === "wishlist" || urlPolicy === "catalog"
      ? urlPolicy
      : clientSavedPolicy === "inventory" || clientSavedPolicy === "wishlist" || clientSavedPolicy === "catalog"
        ? clientSavedPolicy
        : "inventory");

  useEffect(() => {
    if (typeof window !== "undefined" && window.sessionStorage) {
      if (window.sessionStorage.getItem("iqoqo_auto_start_camera") === "true") {
        window.sessionStorage.removeItem("iqoqo_auto_start_camera");
        queueMicrotask(() => setAutoStart(true));
      }
    }
  }, []);

  const inFlightBarcodesRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (activeFormatOverride === null) return;
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("iqoqo_scanner_media_type", activeFormatOverride);
    }
  }, [activeFormatOverride]);

  useEffect(() => {
    if (policyOverride === null) return;
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem("iqoqo_scanner_policy", policyOverride);
    }
  }, [policyOverride]);

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
          queryClient.invalidateQueries({ queryKey: queryKeys.itemsAll });
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
    if (fmt === "magazine") return "magazine";
    if (fmt === "book") return "book";
    return "";
  };

  const handleFound = useCallback(
    async (isbn: string, meta: IsbnMeta) => {
      // Prefer the backend-normalized identifier/barcode if available
      const canonicalId = meta.identifier || meta.barcode || meta.isbn || isbn;

      if (meta.serial_disambiguation || meta.status === "serial_disambiguation") {
        inFlightBarcodesRef.current.delete(canonicalId);
        await triggerScanHaptic();
        setSerialDisambiguation(meta);
        return;
      }

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
          queryClient.invalidateQueries({ queryKey: ["wishlist"] });
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
      let timeoutId: ReturnType<typeof setTimeout> | undefined;
      const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error(t("bottomSheet.lookupTimedOut"))), 10000);
      });
      const data = await Promise.race([apiFetch<IsbnMeta>(url), timeoutPromise]).finally(() => {
        if (timeoutId) clearTimeout(timeoutId);
      });
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

  const handleExtractComplete = useCallback(
    (
      data: {
        Title?: string;
        Authors?: string[];
        Publisher?: string;
        issn?: string;
        indeks?: string;
        ean_addon?: string;
        issue_number?: string;
        cumulative_issue_number?: number;
        publication_month?: number;
        publication_year?: number;
        cover_headline?: string;
      },
      file?: File
    ) => {
      setTitle(data.Title || "");
      setAuthor(data.Authors?.join(", ") || "");
      const hasSerialFields = Boolean(
        data.issn ||
        data.indeks ||
        data.ean_addon ||
        data.issue_number ||
        data.cumulative_issue_number != null ||
        data.cover_headline ||
        activeFormat === "magazine"
      );
      if (hasSerialFields) {
        if (data.issn || data.indeks || data.ean_addon || data.issue_number || data.cumulative_issue_number != null) {
          setActiveFormat("magazine");
        }
        setSerialDefaults(prev => {
          const base = prev ?? {};
          return {
            ...base,
            publisher: data.Publisher || base.publisher,
            issn: data.issn || base.issn,
            issueNumber: data.issue_number || base.issueNumber,
            cumulativeIssueNumber:
              data.cumulative_issue_number != null ? String(data.cumulative_issue_number) : base.cumulativeIssueNumber,
            publicationMonth: data.publication_month != null ? String(data.publication_month) : base.publicationMonth,
            year: data.publication_year != null ? String(data.publication_year) : base.year,
            eanAddon: data.ean_addon || base.eanAddon,
            coverHeadline: data.cover_headline || base.coverHeadline,
          };
        });
      }
      if (file) setSnappedCover(file);
      setInitialIdentifier("");
      setShowManual(true);
      toast.success("Cover metadata extracted! Please review.");
    },
    [activeFormat]
  );

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
          .filter(a => Boolean(a) && !["unknown", "n/a", "none"].includes(a.toLowerCase()))
      : [];

    let explicitDate = data.year || undefined;
    if (explicitDate && /^\d{4}$/.test(explicitDate)) {
      const monthNum = Number(data.publicationMonth);
      const paddedMonth =
        Number.isInteger(monthNum) && monthNum >= 1 && monthNum <= 12 ? String(monthNum).padStart(2, "0") : "01";
      explicitDate = `${explicitDate}-${paddedMonth}-01`;
    }

    const apiFormat = mapFormatToApi(data.format);

    const payload = {
      Title: data.title || "Unknown",
      Authors: authors,
      Format: apiFormat,
      ISBN: data.identifier || undefined,
      PublicationDate: explicitDate,
      Publisher: data.publisher || undefined,
      ...(data.format === "magazine" || data.issn
        ? {
            work_kind: "serial",
            ...(data.issn ? { issn: data.issn } : {}),
            ...(data.issueNumber ? { issue_number: data.issueNumber } : {}),
            ...(data.cumulativeIssueNumber ? { cumulative_issue_number: Number(data.cumulativeIssueNumber) } : {}),
            ...(data.publicationMonth ? { publication_month: Number(data.publicationMonth) } : {}),
            ...(data.year && /^\d{4}$/.test(data.year) ? { publication_year: Number(data.year) } : {}),
            ...(data.eanAddon ? { ean_addon: data.eanAddon } : {}),
            ...(data.coverHeadline ? { cover_headline: data.coverHeadline } : {}),
          }
        : {}),
      ...(policy === "wishlist" ? { collection_status: "wish_list" } : {}),
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
          const resizedCover = await resizeImageFile(coverToUpload, {
            maxDimension: COVER_MAX_DIMENSION,
            quality: COVER_JPEG_QUALITY,
          });
          const coverFormData = new FormData();
          coverFormData.append("cover", resizedCover);
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
        } else if (policy === "wishlist") {
          toast.success(`"${payload.Title}" added to your wishlist!`);
        } else {
          toast.success(`"${payload.Title}" added to your library!`);
        }

        if (policy === "wishlist") {
          router.push(item?.manifestation_id ? `/manifestation/${item.manifestation_id}` : "/wishlist");
        } else if (response.data?.item_id) {
          router.push(`/item/${response.data.item_id}`);
        }
      },
      onError: async (error: unknown) => {
        const isOffline =
          (typeof navigator !== "undefined" && !navigator.onLine) || (axios.isAxiosError(error) && !error.response);

        if (isOffline) {
          // If network error occurred during submission, save to offline manual queue
          await enqueueOfflineManualEntry(payload);
          toast.info(`Network unreachable: "${payload.Title}" queued locally for sync.`);
          setShowManual(false);
        } else {
          const errData = (error as { response?: { data?: { error?: string } } })?.response?.data;
          const msg = errData?.error || (error as Error)?.message || "Failed to create item";
          toast.error(`Error: ${msg}`);
        }
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
          rightAccessory={
            !result && !showManual ? (
              <BatchScanToggle
                compact
                enabled={isBatchMode}
                onToggle={setBatchMode}
                queueCount={scannedQueue.length}
                recentItems={scannedQueue}
                onClearQueue={clearQueue}
              />
            ) : undefined
          }
        >
          {!result && !showManual && (
            <form
              onSubmit={handleQuickLookup}
              data-testid="unified-lookup-form"
              className="flex w-full min-w-0 h-9 items-center rounded-xl bg-background/85 backdrop-blur-md border border-border/40 shadow-sm px-3 focus-within:border-primary/60"
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
                type="submit"
                size="sm"
                disabled={!quickQuery.trim() || isQuickSearching}
                className="h-7 px-2.5 text-xs ml-1 shrink-0 rounded-lg"
              >
                {isQuickSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("unifiedLookup.searchButton")}
              </Button>
            </form>
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

        {serialDisambiguation && (
          <SerialDisambiguationModal
            disambiguation={serialDisambiguation}
            onSelectIssue={issue => {
              setSerialDisambiguation(null);
              const issueBarcode = issue.full_barcode || issue.ean || serialDisambiguation.ean || "";
              setResult({
                isbn: issueBarcode,
                meta: {
                  Title: issue.title || serialDisambiguation.title || serialDisambiguation.Title || "",
                  Authors: [],
                  title: issue.title || serialDisambiguation.title || serialDisambiguation.Title || "",
                  format: "magazine",
                  manifestation_id: issue.manifestation_id,
                  issn: serialDisambiguation.issn,
                  issue_number: issue.issue_number,
                  cumulative_issue_number: issue.cumulative_issue_number,
                  publication_year: issue.publication_year,
                  publication_month: issue.publication_month,
                  ean: issue.ean || serialDisambiguation.ean,
                  ean_addon: issue.ean_addon,
                  full_barcode: issue.full_barcode,
                  cover_url: issue.cover_url || undefined,
                  already_in_db: true,
                },
              });
            }}
            onAddNewIssue={() => {
              const prefill = serialDisambiguation.prefill;
              setActiveFormat("magazine");
              setTitle(prefill?.title || serialDisambiguation.title || "");
              setInitialIdentifier(prefill?.ean || serialDisambiguation.ean || serialDisambiguation.issn || "");
              setSerialDefaults({
                publisher: prefill?.publisher || serialDisambiguation.publisher || "",
                issn: prefill?.issn || serialDisambiguation.issn || "",
              });
              setSerialDisambiguation(null);
              setShowManual(true);
            }}
            onSnapCoverAutoFill={(extracted, file) => {
              const prefill = serialDisambiguation.prefill;
              setActiveFormat("magazine");
              setTitle(prefill?.title || serialDisambiguation.title || extracted.Title || "");
              setAuthor("");
              setInitialIdentifier(prefill?.ean || serialDisambiguation.ean || serialDisambiguation.issn || "");
              setSerialDefaults({
                publisher: prefill?.publisher || serialDisambiguation.publisher || extracted.Publisher || "",
                issn: prefill?.issn || serialDisambiguation.issn || extracted.issn || "",
                issueNumber: extracted.issue_number || "",
                cumulativeIssueNumber:
                  extracted.cumulative_issue_number != null ? String(extracted.cumulative_issue_number) : "",
                publicationMonth: extracted.publication_month != null ? String(extracted.publication_month) : "",
                year: extracted.publication_year != null ? String(extracted.publication_year) : "",
                eanAddon: extracted.ean_addon || "",
                coverHeadline: extracted.cover_headline || "",
              });
              setSnappedCover(file);
              setSerialDisambiguation(null);
              setShowManual(true);
              toast.success("Issue details extracted from cover! Please review.");
            }}
            onDismiss={() => setSerialDisambiguation(null)}
          />
        )}

        {showManual && (
          <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
            <ManualEntryForm
              onSubmit={handleManualSubmit}
              onCancel={() => setShowManual(false)}
              initialTitle={title}
              initialAuthors={author}
              initialPublisher={serialDefaults.publisher}
              initialYear={serialDefaults.year}
              initialIssn={serialDefaults.issn}
              initialIssueNumber={serialDefaults.issueNumber}
              initialCumulativeIssueNumber={serialDefaults.cumulativeIssueNumber}
              initialPublicationMonth={serialDefaults.publicationMonth}
              initialEanAddon={serialDefaults.eanAddon}
              initialCoverHeadline={serialDefaults.coverHeadline}
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
