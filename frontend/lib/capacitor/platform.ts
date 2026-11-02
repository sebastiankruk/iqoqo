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

/**
 * Returns whether the application is currently running in a native Capacitor shell
 * (iOS or Android).
 *
 * @returns {boolean} True if running on iOS or Android native platform.
 */
export function isNativeApp(): boolean {
  return typeof window !== "undefined" && Capacitor.isNativePlatform();
}

/**
 * Returns the current platform name ("ios", "android", or "web").
 *
 * @returns {"ios" | "android" | "web"} The platform identifier.
 */
export function getPlatform(): "ios" | "android" | "web" {
  if (typeof window === "undefined") {
    return "web";
  }
  const platform = Capacitor.getPlatform();
  if (platform === "ios" || platform === "android") {
    return platform;
  }
  return "web";
}

/**
 * Returns whether the application is running on Android.
 *
 * @returns {boolean} True if Android native platform.
 */
export function isAndroid(): boolean {
  return getPlatform() === "android";
}

/**
 * Returns whether the application is running on iOS.
 *
 * @returns {boolean} True if iOS native platform.
 */
export function isIOS(): boolean {
  return getPlatform() === "ios";
}
