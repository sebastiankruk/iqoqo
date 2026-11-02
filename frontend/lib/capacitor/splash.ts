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
 * Safely hides the native splash screen if running in a native Capacitor shell.
 *
 * @returns {Promise<void>}
 */
export async function hideSplashScreen(): Promise<void> {
  if (isNativeApp()) {
    try {
      await SplashScreen.hide();
    } catch {
      // Ignore if splash screen was already dismissed
    }
  }
}

/**
 * Shows the native splash screen if running in a native Capacitor shell.
 *
 * @returns {Promise<void>}
 */
export async function showSplashScreen(): Promise<void> {
  if (isNativeApp()) {
    try {
      await SplashScreen.show({
        autoHide: false,
      });
    } catch {
      // Ignore in non-supported environments
    }
  }
}
