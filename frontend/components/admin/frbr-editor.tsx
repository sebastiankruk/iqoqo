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

import { useState, useEffect, useCallback } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getFrbrTree, updateFrbrEntity, type FrbrTree, type FrbrItem } from "@/lib/api/admin";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Save, RotateCcw } from "lucide-react";

interface MetaField {
  key: string;
  value: string;
}

interface FrbrEditorProps {
  manifestationId: number;
  onClose?: () => void;
}

const metaFieldsSchema = z.object({
  metaFields: z.array(z.object({ key: z.string().min(1), value: z.string() })),
});

const workSchema = metaFieldsSchema.extend({
  title: z.string().min(1, "Title is required"),
});

const expressionSchema = metaFieldsSchema.extend({
  content_type: z.string().optional(),
  language: z.string().optional(),
});

const manifestationSchema = metaFieldsSchema.extend({
  isbn13: z.string().optional(),
  upc: z.string().optional(),
  ean: z.string().optional(),
  publisher: z.string().optional(),
  publication_date: z.string().optional(),
});

const itemSchema = metaFieldsSchema.extend({
  status: z.string().optional(),
  condition: z.string().optional(),
});

type WorkFormData = z.infer<typeof workSchema>;
type ExpressionFormData = z.infer<typeof expressionSchema>;
type ManifestationFormData = z.infer<typeof manifestationSchema>;
type ItemFormData = z.infer<typeof itemSchema>;

function transformMetaToFields(meta: Record<string, unknown> | null | undefined): MetaField[] {
  if (!meta || typeof meta !== "object") return [];
  return Object.entries(meta).map(([key, value]) => ({
    key,
    value: String(value ?? ""),
  }));
}

function transformFieldsToMeta(fields: MetaField[]): Record<string, unknown> {
  return fields.reduce(
    (acc, field) => {
      if (field.key.trim()) {
        acc[field.key.trim()] = field.value;
      }
      return acc;
    },
    {} as Record<string, unknown>
  );
}

function InputField({
  name,
  defaultValue,
  placeholder,
  required,
  className = "",
}: {
  name: string;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <input
      name={name}
      defaultValue={defaultValue}
      placeholder={placeholder}
      required={required}
      className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    />
  );
}

function WorkEditor({ tree, onSubmit }: { tree: FrbrTree; onSubmit: (data: WorkFormData) => Promise<void> }) {
  const [metaFields, setMetaFields] = useState<MetaField[]>([]);

  useEffect(() => {
    if (tree.work) {
      setMetaFields(transformMetaToFields(tree.work.meta));
    }
  }, [tree.work]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: WorkFormData = {
      title: formData.get("title") as string,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-sm font-medium">Title</label>
        <InputField name="title" defaultValue={tree.work?.title ?? ""} required />
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata (JSONB)</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <input
              placeholder="Key"
              value={field.key}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].key = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-1/3"
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Work
      </Button>
    </form>
  );
}

function ExpressionEditor({
  tree,
  onSubmit,
}: {
  tree: FrbrTree;
  onSubmit: (data: ExpressionFormData) => Promise<void>;
}) {
  const [metaFields, setMetaFields] = useState<MetaField[]>([]);

  useEffect(() => {
    if (tree.expression) {
      setMetaFields(transformMetaToFields(tree.expression.meta));
    }
  }, [tree.expression]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ExpressionFormData = {
      content_type: formData.get("content_type") as string | undefined,
      language: formData.get("language") as string | undefined,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Content Type</label>
          <InputField name="content_type" defaultValue={tree.expression?.content_type ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">Language</label>
          <InputField name="language" defaultValue={tree.expression?.language ?? ""} placeholder="e.g., en, pl" />
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata (JSONB)</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <input
              placeholder="Key"
              value={field.key}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].key = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-1/3"
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Expression
      </Button>
    </form>
  );
}

function ManifestationEditor({
  tree,
  onSubmit,
}: {
  tree: FrbrTree;
  onSubmit: (data: ManifestationFormData) => Promise<void>;
}) {
  const [metaFields, setMetaFields] = useState<MetaField[]>([]);

  useEffect(() => {
    if (tree.manifestation) {
      setMetaFields(transformMetaToFields(tree.manifestation.meta));
    }
  }, [tree.manifestation]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ManifestationFormData = {
      isbn13: formData.get("isbn13") as string | undefined,
      upc: formData.get("upc") as string | undefined,
      ean: formData.get("ean") as string | undefined,
      publisher: formData.get("publisher") as string | undefined,
      publication_date: formData.get("publication_date") as string | undefined,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">ISBN-13</label>
          <InputField name="isbn13" defaultValue={tree.manifestation.isbn13 ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">UPC</label>
          <InputField name="upc" defaultValue={tree.manifestation.upc ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">EAN</label>
          <InputField name="ean" defaultValue={tree.manifestation.ean ?? ""} />
        </div>
        <div>
          <label className="text-sm font-medium">Publisher</label>
          <InputField name="publisher" defaultValue={tree.manifestation.publisher ?? ""} />
        </div>
        <div className="col-span-2">
          <label className="text-sm font-medium">Publication Date</label>
          <InputField
            name="publication_date"
            defaultValue={tree.manifestation.publication_date ?? ""}
            placeholder="YYYY-MM-DD"
          />
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata (JSONB)</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <input
              placeholder="Key"
              value={field.key}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].key = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-1/3"
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Manifestation
      </Button>
    </form>
  );
}

function ItemEditor({ item, onSubmit }: { item: FrbrItem; onSubmit: (data: ItemFormData) => Promise<void> }) {
  const [metaFields, setMetaFields] = useState<MetaField[]>([]);

  useEffect(() => {
    setMetaFields(transformMetaToFields(item.meta));
  }, [item]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: ItemFormData = {
      status: formData.get("status") as string | undefined,
      condition: formData.get("condition") as string | undefined,
      metaFields,
    };
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Status</label>
          <InputField name="status" defaultValue={item.status ?? ""} placeholder="available, lent, lost, wish_list" />
        </div>
        <div>
          <label className="text-sm font-medium">Condition</label>
          <InputField name="condition" defaultValue={item.condition ?? ""} placeholder="Like New, Good, Fair" />
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="font-medium text-sm text-muted-foreground">Dynamic Metadata (JSONB)</h4>
        {metaFields.map((field, index) => (
          <div key={index} className="flex gap-2 items-center">
            <input
              placeholder="Key"
              value={field.key}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].key = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-1/3"
            />
            <input
              placeholder="Value"
              value={field.value}
              onChange={e => {
                const newFields = [...metaFields];
                newFields[index].value = e.target.value;
                setMetaFields(newFields);
              }}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setMetaFields(metaFields.filter((_, i) => i !== index))}
            >
              <Trash2 className="w-4 h-4 text-destructive" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setMetaFields([...metaFields, { key: "", value: "" }])}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Field
        </Button>
      </div>
      <Button type="submit">
        <Save className="w-4 h-4 mr-2" />
        Save Item
      </Button>
    </form>
  );
}

export function FrbrEditor({ manifestationId }: FrbrEditorProps) {
  const [tree, setTree] = useState<FrbrTree | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("manifestation");

  const fetchTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getFrbrTree(manifestationId);
      setTree(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load FRBR tree";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [manifestationId]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  const handleWorkSubmit = async (data: WorkFormData) => {
    if (!tree?.work) return;
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("work", tree.work.id, { title: data.title, meta });
      toast.success("Work updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update work: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleExpressionSubmit = async (data: ExpressionFormData) => {
    if (!tree?.expression) return;
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("expression", tree.expression.id, {
        content_type: data.content_type,
        language: data.language,
        meta,
      });
      toast.success("Expression updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update expression: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleManifestationSubmit = async (data: ManifestationFormData) => {
    if (!tree?.manifestation) return;
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("manifestation", tree.manifestation.id, {
        isbn13: data.isbn13,
        upc: data.upc,
        ean: data.ean,
        publisher: data.publisher,
        publication_date: data.publication_date,
        meta,
      });
      toast.success("Manifestation updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update manifestation: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleItemSubmit = async (data: ItemFormData, itemId: number) => {
    try {
      const meta = transformFieldsToMeta(data.metaFields);
      await updateFrbrEntity("item", itemId, {
        status: data.status,
        condition: data.condition,
        meta,
      });
      toast.success("Item updated successfully");
      await fetchTree();
    } catch (err) {
      toast.error(`Failed to update item: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin w-8 h-8" />
      </div>
    );
  }

  if (error || !tree) {
    return (
      <div className="text-center p-8">
        <p className="text-destructive">{error ?? "Failed to load FRBR hierarchy"}</p>
        <Button variant="outline" className="mt-4" onClick={fetchTree}>
          <RotateCcw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex border-b">
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "work"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("work")}
        >
          F1 Work
        </button>
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "expression"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("expression")}
        >
          F2 Expression
        </button>
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "manifestation"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("manifestation")}
        >
          F3 Manifestation
        </button>
        <button
          type="button"
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "items"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("items")}
        >
          F5 Items ({tree.items.length})
        </button>
      </div>

      {activeTab === "work" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Work</CardTitle>
            <CardDescription>The creative foundation (F1 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.work ? (
              <WorkEditor tree={tree} onSubmit={handleWorkSubmit} />
            ) : (
              <p className="text-muted-foreground">No Work associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "expression" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Expression</CardTitle>
            <CardDescription>The intellectual artistic form (F2 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.expression ? (
              <ExpressionEditor tree={tree} onSubmit={handleExpressionSubmit} />
            ) : (
              <p className="text-muted-foreground">No Expression associated with this manifestation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "manifestation" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Manifestation</CardTitle>
            <CardDescription>The physical embodiment (F3 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            <ManifestationEditor tree={tree} onSubmit={handleManifestationSubmit} />
          </CardContent>
        </Card>
      )}

      {activeTab === "items" && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Items</CardTitle>
            <CardDescription>Individual copies (F5 Entity)</CardDescription>
          </CardHeader>
          <CardContent>
            {tree.items.length === 0 ? (
              <p className="text-muted-foreground">No items associated with this manifestation.</p>
            ) : (
              <div className="space-y-4">
                {tree.items.map(item => (
                  <div key={item.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">Item #{item.id}</span>
                      <span className="text-sm text-muted-foreground">Owner: {item.owner_id}</span>
                    </div>
                    <ItemEditor item={item} onSubmit={data => handleItemSubmit(data, item.id)} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
