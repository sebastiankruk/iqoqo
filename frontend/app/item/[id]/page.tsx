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

import ItemPageClient from "./item-page-client";

interface Props {
  params: Promise<{ id: string }>;
}

/**
 * Generates static params for routing.
 *
 * @returns Array of default route parameters.
 */
export function generateStaticParams() {
  return [{ id: "_" }];
}

/**
 * Server component wrapper that renders client-side ItemPageClient.
 *
 * @param {Props} props - Page props containing params promise.
 * @returns {JSX.Element} The rendered client page.
 */
export default function Page(props: Props) {
  return <ItemPageClient {...props} />;
}
