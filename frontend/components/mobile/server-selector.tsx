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

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Server, CheckCircle2, XCircle } from "lucide-react";
import { setInstanceUrl, setInstanceName } from "@/lib/capacitor/storage";

type VerificationState = "idle" | "verifying" | "success" | "error";

/**
 * HASS-style instance picker shown on first launch in the native app.
 * The user enters the base URL of their iqoqo backend, the component
 * verifies reachability against /api/health, then persists the URL via
 * Capacitor Preferences before routing to /login.
 *
 * @returns {JSX.Element} The server selector UI.
 */
export function ServerSelector() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [state, setState] = useState<VerificationState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [instanceInfo, setInstanceInfo] = useState<{ name?: string } | null>(null);

  /** Verify the entered URL points to a valid iqoqo instance. */
  async function handleVerify() {
    const cleanUrl = url.replace(/\/+$/, "");
    setState("verifying");
    setErrorMsg("");

    try {
      const res = await fetch(`${cleanUrl}/api/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(10_000),
      });

      if (!res.ok) throw new Error(`Server responded with ${res.status}`);

      const data = (await res.json()) as { instance_name?: string };
      setInstanceInfo({ name: data.instance_name ?? cleanUrl });
      setState("success");
    } catch (err) {
      setState("error");
      setErrorMsg(err instanceof Error ? err.message : "Could not reach server");
    }
  }

  /** Persist the verified instance URL and navigate to login. */
  async function handleConnect() {
    const cleanUrl = url.replace(/\/+$/, "");
    await setInstanceUrl(cleanUrl);
    if (instanceInfo?.name) {
      await setInstanceName(instanceInfo.name);
    }
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 bg-background">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <Server className="mx-auto h-12 w-12 text-muted-foreground" />
          <h1 className="text-2xl font-bold">Connect to iqoqo</h1>
          <p className="text-sm text-muted-foreground">Enter the URL of your iqoqo instance</p>
        </div>

        <div className="space-y-4">
          <Input
            type="url"
            placeholder="https://library.example.com"
            value={url}
            onChange={e => {
              setUrl(e.target.value);
              setState("idle");
            }}
            disabled={state === "verifying"}
          />

          {state === "error" && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <XCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {state === "success" && instanceInfo && (
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>Connected: {instanceInfo.name}</span>
            </div>
          )}

          {state !== "success" ? (
            <Button onClick={handleVerify} disabled={!url.trim() || state === "verifying"} className="w-full">
              {state === "verifying" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Verify Connection
            </Button>
          ) : (
            <Button onClick={handleConnect} className="w-full">
              Continue to Login
            </Button>
          )}
        </div>

        <p className="text-xs text-center text-muted-foreground">
          Don&apos;t have an instance? Visit iqoqo.cc to learn how to set one up.
        </p>
      </div>
    </div>
  );
}
