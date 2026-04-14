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

import { describe, it, expect } from 'vitest';
import { PermissionName } from '../lib/permissions';

describe('PermissionName Enum', () => {
  it('should have consistent verb:noun values', () => {
    Object.values(PermissionName).forEach((value) => {
      expect(value).toMatch(/^[a-z_]+:[a-z_]+$/);
    });
  });

  it('should have metadata permissions', () => {
    expect(PermissionName.READ_METADATA).toBe('read:metadata');
    expect(PermissionName.WRITE_METADATA).toBe('write:metadata');
  });

  it('should have new cover permissions', () => {
    expect(PermissionName.EDIT_COVER).toBe('edit:cover');
  });

  it('should not contain legacy content permissions', () => {
    const values = Object.values(PermissionName) as string[];
    expect(values).not.toContain('read:content');
    expect(values).not.toContain('write:content');
  });
});
