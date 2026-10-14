## Purpose

Enables users viewing collection cards or item listings to navigate up the FRBR ontology hierarchy directly to parent Work and Expression pages.

## ADDED Requirements

### Requirement: Collection views provide direct parent Work and Expression links
The collection views SHALL render distinct, accessible navigation links or chips pointing to the parent Work (`/work/:id`) and Expression for each displayed collection entry that belongs to a resolved FRBR hierarchy.

#### Scenario: User clicks parent Work link from collection card
- **WHEN** a user views an item card in the collection view and clicks the Work title or badge link
- **THEN** the system navigates directly to the corresponding Work page without intermediate modal dialogs

#### Scenario: Collection item with unlinked Work or Expression
- **WHEN** a collection item lacks a linked parent Work or Expression record
- **THEN** the collection card gracefully suppresses the parent link without layout breakage or dead navigation links

### Requirement: FRBR breadcrumbs displayed in item header
The item detail surface SHALL display an explicit parent breadcrumb indicating the full FRBR lineage (Work -> Expression -> Manifestation -> Item) where each ancestor links to its respective detail page.

#### Scenario: User navigates upward via FRBR lineage breadcrumb
- **WHEN** a user views an Item detail page and clicks the parent Expression or Work breadcrumb
- **THEN** the system navigates directly to the clicked ancestor entity page
