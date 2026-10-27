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
import { useTranslations } from "next-intl";
import { ShieldCheck, ShieldAlert, Key, Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";

interface TotpSetupProps {
  totpEnabled: boolean;
  onStatusChanged: () => void | Promise<void>;
}

interface EnrollResponse {
  secret: string;
  provisioning_uri: string;
  recovery_codes: string[];
  qr_code: string;
}

/**
 * Two-Factor Authentication (TOTP 2FA) setup and management card.
 *
 * @param props - Component properties
 * @param props.totpEnabled - Whether 2FA is currently active
 * @param props.onStatusChanged - Callback when 2FA state changes
 * @returns {JSX.Element} The component
 */
export function TotpSetup({ totpEnabled, onStatusChanged }: TotpSetupProps) {
  const t = useTranslations("Profile");

  // Enrollment state
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [enrollData, setEnrollData] = useState<EnrollResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [isLoadingEnroll, setIsLoadingEnroll] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);

  // Disable 2FA state
  const [isDisableDialogOpen, setIsDisableDialogOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [isDisabling, setIsDisabling] = useState(false);

  const startEnrollment = async () => {
    setIsLoadingEnroll(true);
    try {
      const res = await apiClient.post<EnrollResponse>("/auth/2fa/enroll");
      setEnrollData(res.data);
      setVerificationCode("");
      setIsEnrollModalOpen(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("disableFailed");
      toast.error(msg);
    } finally {
      setIsLoadingEnroll(false);
    }
  };

  const verifyAndEnable = async () => {
    const code = verificationCode.trim();
    if (!code || code.length !== 6) {
      toast.error(t("validCodeRequired"));
      return;
    }

    setIsVerifying(true);
    try {
      await apiClient.post("/auth/2fa/verify", { code });
      toast.success(t("totpEnabledSuccess"));
      setIsEnrollModalOpen(false);
      setEnrollData(null);
      await onStatusChanged();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("invalidCode");
      toast.error(msg);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDisable = async () => {
    if (!disablePassword && !disableCode) {
      toast.error(t("disableCredentialsRequired"));
      return;
    }

    setIsDisabling(true);
    try {
      await apiClient.post("/auth/2fa/disable", {
        password: disablePassword.trim() || undefined,
        code: disableCode.trim() || undefined,
      });
      toast.success(t("totpDisabledSuccess"));
      setIsDisableDialogOpen(false);
      setDisablePassword("");
      setDisableCode("");
      await onStatusChanged();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("disableFailed");
      toast.error(msg);
    } finally {
      setIsDisabling(false);
    }
  };

  const copySecretToClipboard = () => {
    if (!enrollData?.secret) return;
    navigator.clipboard.writeText(enrollData.secret);
    setCopiedSecret(true);
    toast.success(t("copiedToClipboard"));
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const copyRecoveryCodes = () => {
    if (!enrollData?.recovery_codes) return;
    navigator.clipboard.writeText(enrollData.recovery_codes.join("\n"));
    setCopiedCodes(true);
    toast.success(t("copiedToClipboard"));
    setTimeout(() => setCopiedCodes(false), 2000);
  };

  return (
    <div className="p-4 border rounded-lg bg-card space-y-4" data-testid="totp-setup-card">
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">{t("twoFactorAuth")}</h2>
            {totpEnabled ? (
              <Badge variant="default" className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                {t("enabled")}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5" />
                {t("disabled")}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{t("twoFactorAuthDesc")}</p>
        </div>

        {totpEnabled ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setIsDisableDialogOpen(true)}
            data-testid="disable-2fa-button"
          >
            {t("disable2FA")}
          </Button>
        ) : (
          <Button
            variant="default"
            size="sm"
            onClick={startEnrollment}
            disabled={isLoadingEnroll}
            data-testid="enable-2fa-button"
          >
            {isLoadingEnroll ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Key className="w-4 h-4 mr-2" />}
            {t("enable2FA")}
          </Button>
        )}
      </div>

      {/* ── Enrollment Dialog ── */}
      <Dialog open={isEnrollModalOpen} onOpenChange={setIsEnrollModalOpen}>
        <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto" data-testid="totp-enroll-dialog">
          <DialogHeader>
            <DialogTitle>{t("setupTwoFactorAuth")}</DialogTitle>
            <DialogDescription>{t("scanQrCodeDesc")}</DialogDescription>
          </DialogHeader>

          {enrollData && (
            <div className="space-y-4 py-2">
              {/* QR Code */}
              <div className="flex justify-center p-3 bg-white rounded-lg border w-fit mx-auto">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={enrollData.qr_code} alt="TOTP QR Code" className="w-48 h-48" data-testid="totp-qr-code" />
              </div>

              {/* Secret Key */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">{t("secretKeyManual")}</label>
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-muted px-2 py-1.5 rounded flex-1 font-mono break-all select-all">
                    {enrollData.secret}
                  </code>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={copySecretToClipboard}
                    className="h-8 px-2"
                  >
                    {copiedSecret ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                  </Button>
                </div>
              </div>

              {/* Recovery Codes */}
              <div className="space-y-1.5 border-t pt-3">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-foreground">{t("recoveryCodes")}</label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={copyRecoveryCodes}
                    className="h-7 text-xs px-2"
                  >
                    {copiedCodes ? (
                      <Check className="w-3 h-3 text-green-600 mr-1" />
                    ) : (
                      <Copy className="w-3 h-3 mr-1" />
                    )}
                    {t("copyAll")}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">{t("recoveryCodesDesc")}</p>
                <div className="grid grid-cols-2 gap-1.5 p-2 bg-muted/60 rounded text-xs font-mono text-center">
                  {enrollData.recovery_codes.map((code, idx) => (
                    <span key={idx} className="bg-background/80 py-1 rounded border border-border/50">
                      {code}
                    </span>
                  ))}
                </div>
              </div>

              {/* Verification Code Input */}
              <div className="space-y-1.5 border-t pt-3">
                <label htmlFor="totp-code-input" className="text-sm font-medium">
                  {t("enter6DigitCode")}
                </label>
                <input
                  id="totp-code-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="123456"
                  value={verificationCode}
                  onChange={e => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                  className="w-full h-10 px-3 py-2 text-center text-lg tracking-widest font-mono rounded-md border border-input bg-background"
                  data-testid="totp-verification-input"
                  autoFocus
                />
              </div>
            </div>
          )}

          <DialogFooter className="sm:justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setIsEnrollModalOpen(false)} disabled={isVerifying}>
              {t("cancel")}
            </Button>
            <Button
              type="button"
              onClick={verifyAndEnable}
              disabled={isVerifying || verificationCode.trim().length !== 6}
              data-testid="verify-and-enable-button"
            >
              {isVerifying && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("verifyAndEnable")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Disable 2FA Dialog ── */}
      <Dialog open={isDisableDialogOpen} onOpenChange={setIsDisableDialogOpen}>
        <DialogContent className="sm:max-w-md" data-testid="disable-2fa-dialog">
          <DialogHeader>
            <DialogTitle>{t("disable2FATitle")}</DialogTitle>
            <DialogDescription>{t("disable2FADesc")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <label htmlFor="disable-password" className="text-sm font-medium">
                {t("accountPassword")}
              </label>
              <input
                id="disable-password"
                type="password"
                placeholder={t("currentPassword")}
                value={disablePassword}
                onChange={e => setDisablePassword(e.target.value)}
                className="w-full h-9 px-3 py-2 text-sm rounded-md border border-input bg-background"
                data-testid="disable-password-input"
              />
            </div>

            <div className="text-xs text-center text-muted-foreground">— {t("or")} —</div>

            <div className="space-y-1">
              <label htmlFor="disable-code" className="text-sm font-medium">
                {t("orEnterOtpCode")}
              </label>
              <input
                id="disable-code"
                type="text"
                placeholder={t("otpOrRecoveryPlaceholder")}
                value={disableCode}
                onChange={e => setDisableCode(e.target.value)}
                className="w-full h-9 px-3 py-2 text-sm rounded-md border border-input bg-background font-mono"
                data-testid="disable-code-input"
              />
            </div>
          </div>

          <DialogFooter className="sm:justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDisableDialogOpen(false)}
              disabled={isDisabling}
            >
              {t("cancel")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDisable}
              disabled={isDisabling || (!disablePassword && !disableCode)}
              data-testid="confirm-disable-2fa-button"
            >
              {isDisabling && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              {t("confirmDisable")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
