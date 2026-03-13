// Auto-generated permissions for frontend
export const ItemPermissions = {
  REFETCH_METADATA: 'refetch:metadata' as const,
  REGENERATE_COVER: 'regenerate:cover' as const,
  DELETE_ITEM: 'delete:item' as const,
} as const;

export type ItemPermission = typeof ItemPermissions[keyof typeof ItemPermissions];
