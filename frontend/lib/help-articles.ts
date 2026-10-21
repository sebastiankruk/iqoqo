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
export interface HelpArticle {
  slug: string;
  category: "cataloging" | "federation" | "tools";
  title: Record<"en" | "pl", string>;
  description: Record<"en" | "pl", string>;
  content: Record<"en" | "pl", string>;
}

export const HELP_ARTICLES: HelpArticle[] = [
  {
    slug: "frbr-hierarchy",
    category: "cataloging",
    title: {
      en: "FRBR Hierarchy: Work, Expression, Manifestation, and Item",
      pl: "Hierarchia FRBR: Dzieło, Ekspresja, Manifestacja i Egzemplarz",
    },
    description: {
      en: "Understand how iqoqo structures bibliographic metadata using the IFLA FRBR standard.",
      pl: "Dowiedz się, jak iqoqo organizuje metadane bibliograficzne według standardu IFLA FRBR.",
    },
    content: {
      en: `
# Understanding the FRBR Hierarchy in iqoqo

iqoqo is built from the ground up on the **FRBR (Functional Requirements for Bibliographic Records)** conceptual model. Unlike simple spreadsheets or traditional flat catalog systems, FRBR separates the abstract creative concept from the physical object in your hands.

## The Four Levels of FRBR

1. **Work (Abstract Idea)**:
   - The distinct intellectual or artistic creation.
   - *Example*: *Dune* by Frank Herbert as a story and literary concept.

2. **Expression (Intellectual Realization)**:
   - The realization of a work in a specific language, performance, or version.
   - *Example*: The original English text of *Dune*, or its Polish translation by Marek Marszał.

3. **Manifestation (Physical Publication / Release)**:
   - The physical embodiment of an expression produced by a publisher or manufacturer.
   - Includes ISBN, publisher, publication year, dimensions, and cover art.
   - *Example*: The 2019 hardcover edition of *Dune* published by Ace Books (ISBN 9780441172719).

4. **Item (Your Physical Exemplar)**:
   - A single physical copy owned by a collector.
   - Holds personal tracking data: reading status, physical location on your shelf, condition, loan tracking, and personal barcode.
   - *Example*: Your signed, dog-eared copy sitting on shelf B3.

## Why FRBR Matters for Collectors
- Multiple editions share common authors, genres, and series automatically.
- Translators, illustrators, and narrators belong to Expressions, keeping credits precise.
- You can track multiple physical copies of the same book without duplicating descriptions.
      `,
      pl: `
# Zrozumienie hierarchii FRBR w iqoqo

iqoqo opiera się na modelu pojęciowym **FRBR (Functional Requirements for Bibliographic Records)**. W przeciwieństwie do zwykłych arkuszy kalkulacyjnych, FRBR rozróżnia abstrakcyjną twórczość od konkretnego przedmiotu na półce.

## Cztery poziomy FRBR

1. **Dzieło (Koncepcja abstrakcyjna)**:
   - Wytwór intelektualny lub artystyczny.
   - *Przykład*: *Diuna* Franka Herberta jako koncepcja literacka.

2. **Ekspresja (Realizacja intelektualna)**:
   - Realizacja dzieła w konkretnym języku, wersji lub przekładzie.
   - *Przykład*: Oryginalny angielski tekst *Diuny* lub polski przekład Marka Marszała.

3. **Manifestacja (Wydanie / Publikacja)**:
   - Fizyczne ucieleśnienie ekspresji wydane przez konkretne wydawnictwo.
   - Zawiera numer ISBN, wydawcę, rok wydania, okładkę.
   - *Przykład*: Wydanie w twardej oprawie z 2019 r. wydane przez Rebis (ISBN 9788380620391).

4. **Egzemplarz (Twój fizyczny przedmiot)**:
   - Pojedynczy fizyczny egzemplarz na Twojej półce.
   - Posiada stan zachowania, status przeczytania, lokalizację i historię wypożyczeń.
   - *Przykład*: Twój egzemplarz z dedykacją stojący na półce w salonie.
      `,
    },
  },
  {
    slug: "barcode-scanning",
    category: "tools",
    title: {
      en: "Barcode Scanning & Metadata Ingestion",
      pl: "Skanowanie kodów kreskowych i pobieranie metadanych",
    },
    description: {
      en: "Tips for rapidly cataloging physical books, board games, and vinyl with a webcam or smartphone camera.",
      pl: "Wskazówki dotyczące szybkiego katalogowania książek, gier i płyt za pomocą kamery.",
    },
    content: {
      en: `
# Barcode Scanning & Metadata Ingestion

iqoqo includes a high-performance in-browser scanner powered by ZXing and BarcodeDetector APIs.

## Supported Barcodes
- **ISBN-13 and ISBN-10 (EAN-13)**: For printed books, graphic novels, and audiobooks.
- **UPC-A / EAN-13**: For board games, tabletop expansions, and vinyl pressings.
- **Custom Local Barcodes (Code 128 / QR Codes)**: Printable inventory tags for items without standard manufacturer barcodes.

## Scanning Tips
1. **Lighting**: Ensure even, bright light without severe glares on glossy book dust jackets.
2. **Camera Distance**: Keep the barcode centered and approximately 15–20 cm (6–8 inches) from the lens.
3. **Continuous Mode**: Enable "Continuous Scan" in the scanner toolbar to process whole stacks of books in succession without clicking.
      `,
      pl: `
# Skanowanie kodów kreskowych i pobieranie metadanych

iqoqo posiada wbudowany skaner działający bezpośrednio w przeglądarce, wykorzystujący API ZXing oraz BarcodeDetector.

## Obsługiwane kody kreskowe
- **ISBN-13 i ISBN-10 (EAN-13)**: Książki, komiksy i audiobooki.
- **UPC-A / EAN-13**: Gry planszowe i płyty winylowe.
- **Lokalne kody kreskowe (Code 128 / QR)**: Drukowalne etykiety inwentarzowe.

## Wskazówki dotyczące skanowania
1. **Oświetlenie**: Zadbaj o równomierne oświetlenie bez silnych refleksów światła.
2. **Odległość**: Trzymaj kod w odległości około 15-20 cm od obiektywu.
3. **Tryb ciągły**: Włącz tryb skanowania ciągłego, aby katalogować całe stosy książek jeden po drugim.
      `,
    },
  },
  {
    slug: "federation-and-privacy",
    category: "federation",
    title: {
      en: "Federation, Friends, and Privacy Controls",
      pl: "Federacja, znajomi i ustawienia prywatności",
    },
    description: {
      en: "How ActivityPub federation works in iqoqo, managing consent, and borrowing items across libraries.",
      pl: "Jak działa federacja ActivityPub w iqoqo, zarządzanie zgodami i wypożyczanie między bibliotekami.",
    },
    content: {
      en: `
# Federation & Privacy in iqoqo

iqoqo connects independent instances using the **W3C ActivityPub** protocol, creating a decentralized network of physical libraries.

## Handles & Identity
- Your handle follows standard Fediverse conventions: \`@username@your-instance.com\`.
- You can follow collectors on other iqoqo instances, browse their public collections, and send loan requests.

## Privacy Boundaries
- **Consent Settings**: Under Settings -> Federation Consent, you decide whether your profile and collections are shared with peer instances.
- **Private Items**: Items marked as hidden or owned by accounts with private item visibility are never published to public endpoints, SPARQL runner snapshots, or ActivityPub outboxes.
- **Physical Custody Transfers**: When you lend an item across instances, an immutable custody event is logged to maintain provenance without exposing private personal notes.
      `,
      pl: `
# Federacja i prywatność w iqoqo

iqoqo łączy niezależne instancje przy użyciu protokołu **W3C ActivityPub**, tworząc zdecentralizowaną sieć prywatnych bibliotek.

## Identyfikatory i tożsamość
- Twój identyfikator to standardowy adres Fediverse: \`@username@twoja-instancja.pl\`.
- Możesz obserwować kolekcjonerów z innych instancji i przeglądać ich publiczne zbiory.

## Ochrona prywatności
- **Ustawienia zgód**: W Ustawienia -> Zgody federacyjne decydujesz o udostępnianiu profilu i zbiorów.
- **Prywatne egzemplarze**: Ukryte egzemplarze nigdy nie trafiają do zapytań SPARQL ani publicznych wykazów federacji.
- **Rejestracja wypożyczeń**: Zmiana posiadacza fizycznego egzemplarza zapisuje zdarzenie w rejestrze proweniencji bez ujawniania prywatnych notatek.
      `,
    },
  },
];
