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
import { SplashScreen } from "@capacitor/splash-screen";
import { isNativeApp } from "./platform";

/**
 * Hide the native splash screen with a short fade-out.
 *
 * Should be called once the app shell has fully hydrated (e.g. from the
 * root layout's `useEffect`). A no-op on web.
 */
export async function hideSplash(): Promise<void> {
  if (isNativeApp()) {
    await SplashScreen.hide({ fadeOutDuration: 300 });
  }
}
