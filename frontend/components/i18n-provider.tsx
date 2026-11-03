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

import { useEffect, useState } from "react";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import { LOCALE_CHANGE_EVENT } from "@/lib/locale-cookie";
import { getSavedLocale } from "@/lib/capacitor/locale";
import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

const MESSAGES_MAP: Record<string, AbstractIntlMessages> = {
  en: enMessages as AbstractIntlMessages,
  pl: plMessages as AbstractIntlMessages,
};

/** Props for ClientI18nProvider */
export interface ClientI18nProviderProps {
  initialLocale: string;
  initialMessages: AbstractIntlMessages;
  children: React.ReactNode;
}

/**
 * Client-side internationalization provider.
 * Supports dynamic locale and message switching in static export (Capacitor mobile builds)
 * where there is no server-side request lifecycle to reload messages.
 *
 * @param props - Component props
 * @returns {JSX.Element} The rendered provider
 */
export function ClientI18nProvider({ initialLocale, initialMessages, children }: ClientI18nProviderProps) {
  const [locale, setLocale] = useState<string>(initialLocale);
  const [messages, setMessages] = useState<AbstractIntlMessages>(MESSAGES_MAP[initialLocale] || initialMessages);

  useEffect(() => {
    let isMounted = true;

    // Check device / saved preferences on mount (especially useful in Capacitor WebView)
    getSavedLocale()
      .then(saved => {
        if (isMounted && saved && saved !== locale && MESSAGES_MAP[saved]) {
          setLocale(saved);
          setMessages(MESSAGES_MAP[saved]);
          if (typeof document !== "undefined") {
            document.documentElement.lang = saved;
          }
        }
      })
      .catch(() => {});

    const handleLocaleChange = (event: Event) => {
      const customEvent = event as CustomEvent<{ locale: string }>;
      const nextLocale = customEvent.detail?.locale;
      if (nextLocale && MESSAGES_MAP[nextLocale]) {
        setLocale(nextLocale);
        setMessages(MESSAGES_MAP[nextLocale]);
        if (typeof document !== "undefined") {
          document.documentElement.lang = nextLocale;
        }
      }
    };

    window.addEventListener(LOCALE_CHANGE_EVENT, handleLocaleChange);
    return () => {
      isMounted = false;
      window.removeEventListener(LOCALE_CHANGE_EVENT, handleLocaleChange);
    };
  }, [locale]);

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
