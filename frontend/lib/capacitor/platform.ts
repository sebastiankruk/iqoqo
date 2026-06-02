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
import { Capacitor } from "@capacitor/core";

export type AppPlatform = "ios" | "android" | "web";

/**
 * Return the current runtime platform.
 *
 * @returns {"ios" | "android" | "web"} The active platform.
 */
export function getPlatform(): AppPlatform {
  return Capacitor.getPlatform() as AppPlatform;
}

/**
 * Return true when the app is running inside a native Capacitor WebView.
 *
 * @returns {boolean} Whether the app is running natively.
 */
export function isNativeApp(): boolean {
  return Capacitor.isNativePlatform();
}

/**
 * Return true when running on iOS.
 *
 * @returns {boolean} Whether the current platform is iOS.
 */
export function isIOS(): boolean {
  return getPlatform() === "ios";
}

/**
 * Return true when running on Android.
 *
 * @returns {boolean} Whether the current platform is Android.
 */
export function isAndroid(): boolean {
  return getPlatform() === "android";
}
