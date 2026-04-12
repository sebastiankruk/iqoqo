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

import { GroupManagement } from "@/components/admin/group-management";

/**
 * Roles management page.
 *
 * @returns The roles page component
 */
export default function GroupsPage() {
  const handleCreateGroup = () => {
    console.log("Create new role");
  };

  return (
    <div className="p-6 lg:p-8">
      <GroupManagement onCreateGroup={handleCreateGroup} />
    </div>
  );
}
