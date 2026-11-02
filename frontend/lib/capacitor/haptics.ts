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
 * Capacitor Haptics bridge utility for mobile tactile feedback.
 *
 * All functions are safely guarded by `isNativeApp()` so web browsers
 * and SSR environments execute as harmless no-ops without throwing errors.
 *
 * @module lib/capacitor/haptics
 */
import { Haptics, ImpactStyle, NotificationType } from "@capacitor/haptics";
import { isNativeApp } from "./platform";

/**
 * Triggers a medium tactile impact vibration when a barcode is acquired or tapped.
 *
 * @returns {Promise<void>} Resolves when the haptic impact completes or is ignored.
 */
export async function triggerScanHaptic(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    await Haptics.impact({ style: ImpactStyle.Medium });
  } catch {
    // Hardware without vibration motor or permission errors fail silently
  }
}

/**
 * Triggers a success notification vibration when an item is added to the collection.
 *
 * @returns {Promise<void>} Resolves when the haptic notification completes or is ignored.
 */
export async function triggerSuccessHaptic(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    await Haptics.notification({ type: NotificationType.Success });
  } catch {
    // Fail silently on unsupported hardware
  }
}

/**
 * Triggers an error notification vibration when scanning or adding fails.
 *
 * @returns {Promise<void>} Resolves when the haptic notification completes or is ignored.
 */
export async function triggerErrorHaptic(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    await Haptics.notification({ type: NotificationType.Error });
  } catch {
    // Fail silently on unsupported hardware
  }
}
