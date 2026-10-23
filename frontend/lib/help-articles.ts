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
  category: "cataloging" | "federation" | "tools" | "curation" | "privacy";
  title: Record<"en" | "pl", string>;
  description: Record<"en" | "pl", string>;
  content: Record<"en" | "pl", string>;
}

export const HELP_ARTICLES: HelpArticle[] = [
  {
    slug: "frbr-hierarchy",
    category: "cataloging",
    title: {
      en: "Beyond the Bookshelf: How iqoqo Organizes Your World",
      pl: "Więcej niż półka z książkami: Jak iqoqo porządkuje Twój świat",
    },
    description: {
      en: "Understand how iqoqo structures physical media, translations, and editions using library-grade FRBR ontology.",
      pl: "Dowiedz się, jak iqoqo organizuje nośniki, przekłady i wydania według bibliotecznego modelu FRBR.",
    },
    content: {
      en: `# Beyond the Bookshelf: How iqoqo Organizes Your World

Most cataloging apps were built with a simple, flat assumption: one barcode equals one entry in a database. If you scan a paperback copy of Frank Herbert's *Dune*, you get a row in a table. If you buy the hardcover 50th Anniversary edition, you get a second, completely disconnected row. If you also own the audiobook, the 2021 Denis Villeneuve Blu-ray, and the *Dune: Imperium* board game, a traditional app treats them as five unrelated strangers cluttering your shelf.

**iqoqo is different.** Under the hood, iqoqo is powered by **FRBR** (*Functional Requirements for Bibliographic Records*)—a semantic philosophy developed by library scientists and ontologists to model how human creativity actually works in the real world. 

Instead of a flat spreadsheet of barcodes, iqoqo organizes your catalog into a four-tier hierarchy: **Work**, **Expression**, **Manifestation**, and **Item** (often called the **WEMI** model).

---

## The Four Pillars of FRBR

To understand how iqoqo thinks about your collection, imagine a single creative spark traveling from an author's mind all the way to the physical shelf in your living room:

![The Four Pillars of FRBR: Work, Expression, Manifestation, and Item](/images/help/frbr-pillars.jpg)

### 1. Work (F1): The Pure Idea

A **Work** is a distinct intellectual or artistic creation. Think of it as the abstract concept in the creator's head before a single word is printed or a single note is pressed onto vinyl.

* **Examples:** Homer's *Odyssey*, Pink Floyd's *The Dark Side of the Moon*, the board game *Catan*, or the 1994 Rock in Rio concert event.

* **Why it matters to you:** At the Work level, iqoqo groups everything that shares the same soul. Your overall appreciation of a story, its thematic tags, and its place in a broader series live right here.

### 2. Expression (F2): How the Idea is Told

An **Expression** is the specific intellectual or artistic realization of a Work. Whenever a Work is translated, narrated, abridged, arranged, or remastered, a new Expression is born.

* **Examples:** 
  * Emily Wilson's 2018 English verse translation of the *Odyssey* vs. Robert Fagles' 1996 translation.

  * The 2011 James Guthrie 5.1 Surround Sound remaster of *The Dark Side of the Moon* vs. the original 1973 stereo mix.

* **Why it matters to you:** Maybe you loved the story of a novel (the *Work*), but you thought the English translation or the audiobook narrator (the *Expression*) was terrible. iqoqo lets you distinguish between the two!

### 3. Manifestation (F3): The Published Package

A **Manifestation** is the physical or digital embodiment of an Expression. This is the level where barcodes (ISBN, EAN, UPC), publishers, page counts, box dimensions, and release dates appear.

* **Examples:** The 2003 Penguin Classics trade paperback with the black spine; the 180-gram gatefold vinyl pressing released by Harvest Records; the PlayStation 5 SteelBook edition of a video game.

* **Why it matters to you:** Collectors care deeply about *which* edition they own or want to buy. Manifestations hold the cover art, the physical format (Hardcover, Blu-ray, Vinyl, Meeple-heavy Board Game Box), and external catalog links (OpenLibrary, MusicBrainz, BGG, IGDB, TMDB).

### 4. Item (F4): The Copy in Your Hands

An **Item** is a single, tangible exemplar of a Manifestation—the actual object sitting on your bookshelf, in your Kallax cube, or on your hard drive.

* **Examples:** *Your* copy of the Penguin Classics paperback—the one with the coffee stain on page 42, your personal ex-libris stamp, and a custom QR inventory sticker on the inside cover.

* **Why it matters to you:** You don't lend an "ISBN" to a friend; you lend *your specific copy*. Privacy settings, lending statuses, acquisition dates, purchase prices, and physical shelf locations are all tracked at the Item level.

---

## Why FRBR Makes iqoqo Unique: Beyond Just Books

Because iqoqo separates the *abstract creation* from the *physical carrier*, it is not limited to books. A traditional book-tracking app breaks down the moment you try to catalog a vinyl record or a jigsaw puzzle, because its database is hardwired for \`Author\`, \`Pages\`, and \`ISBN\`.

In iqoqo, our ontology adapts dynamically across your entire cultural life:

| Media Domain | Work (F1) | Expression (F2) | Manifestation (F3) | Item (F4) |
| :--- | :--- | :--- | :--- | :--- |
| **Books & Comics** | The Novel / Graphic Novel | Original text, Translation, Illustrated edition | Hardcover, Paperback, ePub (ISBN) | Your signed copy on Shelf B |
| **Music & Audio** | Studio Album / Symphony / Live Concert | 1973 Stereo Mix, 2023 Remaster, Live Recording | 2xLP Gatefold Vinyl, SACD, Digital FLAC | Your mint-condition Japanese pressing |
| **Movies & TV** | Feature Film / Miniseries | Theatrical Cut, Director's Cut, Dubbed Version | 4K UHD + Blu-ray Combo Pack | Disc in your media cabinet |
| **Board Games** | Core Game Design / Expansion | 1st Edition Rules, Revised 2nd Edition Rules | Multilingual Retail Box, Kickstarter Deluxe | Your box (with custom 3D-printed inserts!) |
| **Video Games** | Game Title | Original Release, Game of the Year Patch | PS5 Physical Disc, Switch Cartridge, Steam Digital | Your cartridge lent to a friend |
| **Puzzles** | Artwork / Illustration | 1000-Piece Cut Layout, Panoramic Cut | Ravensburger 2022 Retail Box | Your box (missing 1 piece!) |

---

## Everyday Superpowers Unlocked by FRBR

You don't need a degree in library science to use iqoqo—when you scan a barcode, the system builds this four-layer tree for you automatically in milliseconds. Here is what that structure gives you every day:

1. **Zero Clutter, Maximum Detail:** When you browse your Collection, you can see all your editions grouped cleanly under a single Work, or pivot to view every individual physical copy you own.
2. **Smarter Wishlists:** When you add something to your Wishlist, you can choose *how* specific you want to be. Just want to read *Dune* in any format? Wishlist the **Work**. Hunting specifically for the 1965 Chilton Books first-edition hardcover? Wishlist that exact **Manifestation**.
3. **Flexible Reading & Playing Roadmaps:** In your **Roadmaps** (accessible right from your Collection view), you can plan your next reading or gaming marathon by targeting abstract Works, specific translations, or even a specific physical Item you borrowed from a friend and need to return by Friday.
4. **Targeted Ratings & Reviews:** Leave a 5-star review on a **Work** because the story or game mechanics are brilliant, while leaving a 2-star warning on a specific **Manifestation** because the publisher used thin, flimsy cardstock in that particular printing.
`,
      pl: `# Więcej niż półka z książkami: Jak iqoqo porządkuje Twój świat

Większość aplikacji do katalogowania powstała na prostym, płaskim założeniu: jeden kod kreskowy to jeden wiersz w bazie danych. Jeśli zeskanujesz wydanie kieszonkowe *Diuny* Franka Herberta, dostajesz wiersz w tabeli. Jeśli kupisz jubileuszowe wydanie w twardej oprawie, otrzymujesz drugi, całkowicie odrębny wpis. A gdy posiadasz jeszcze audiobook, film na Blu-ray z 2021 roku oraz grę planszową *Dune: Imperium*, tradycyjna aplikacja traktuje je jako pięć obcych sobie pozycji zaśmiecających wirtualną półkę.

**iqoqo działa inaczej.** Sercem systemu jest **FRBR** (*Functional Requirements for Bibliographic Records*) — koncepcja semantyczna opracowana przez bibliotekoznawców i ontologów, aby odzwierciedlać to, jak twórczość funkcjonuje w świecie rzeczywistym.

Zamiast płaskiego arkusza kalkulacyjnego, iqoqo organizuje Twój katalog w czteropoziomową hierarchię: **Dzieło (Work)**, **Ekspresja (Expression)**, **Manifestacja (Manifestation)** oraz **Egzemplarz (Item)** — w skrócie model **WEMI**.

---

## Cztery filary modelu FRBR

Aby zrozumieć sposób myślenia iqoqo, wyobraź sobie twórczą myśl wędrującą z umysłu autora aż na fizyczną półkę w Twoim salonie:

![Cztery filary FRBR: Dzieło, Ekspresja, Manifestacja i Egzemplarz](/images/help/frbr-pillars.jpg)

### 1. Dzieło (F1): Czysta idea

**Dzieło** to odrębna kreacja intelektualna lub artystyczna. To abstrakcyjny pomysł w głowie twórcy, zanim jeszcze pierwsze słowo trafi do druku lub nuta na płytę winylową.

* **Przykłady:** *Odyseja* Homera, album *The Dark Side of the Moon* zespołu Pink Floyd, gra planszowa *Catan* czy koncert na festiwalu Rock in Rio 1994.

* **Dlaczego ma to znaczenie:** Na poziomie Dzieła iqoqo łączy wszystko, co dzieli tę samą duszę. Twoja ocena opowieści, tagi tematyczne i przynależność do cyklu wydawniczego żyją właśnie tutaj.

### 2. Ekspresja (F2): Sposób opowiedzenia idei

**Ekspresja** to konkretna realizacja intelektualna lub artystyczna Dzieła. Za każdym razem, gdy Dzieło jest tłumaczone, czytane przez lektora, aranżowane na nowo lub remasterowane, rodzi się nowa Ekspresja.

* **Przykłady:**

  * Przekład *Władcy Pierścieni* Marii Skibniewskiej a przekład Jerzego Łozińskiego.

  * Remaster 5.1 Surround Sound albumu *The Dark Side of the Moon* Jamesa Guthriego z 2011 r. a oryginalny miks stereo z 1973 r.

* **Dlaczego ma to znaczenie:** Możesz kochać fabułę powieści (*Dzieło*), ale nie znosić konkretnego tłumaczenia lub lektora audiobooka (*Ekspresja*). iqoqo pozwala Ci to precyzyjnie rozróżnić!

### 3. Manifestacja (F3): Wydanie / Publikacja

**Manifestacja** to fizyczne lub cyfrowe ucieleśnienie Ekspresji. Na tym poziomie pojawiają się kody kreskowe (ISBN, EAN, UPC), wydawnictwa, liczba stron, format pudełka i daty premier.

* **Przykłady:** Wydanie kieszonkowe z czarnym grzbietem z 2003 roku; 180-gramowy winyl w okładce gatefold; limitowane wydanie gry na PlayStation 5 w metalowym pudełku (SteelBook).

* **Dlaczego ma to znaczenie:** Kolekcjonerzy zwracają ogromną uwagę na to, *które* wydanie posiadają lub na które polują. Manifestacje przechowują okładki, fizyczny nośnik (twarda oprawa, Blu-ray, winyl) oraz powiązania z zewnętrznymi katalogami (OpenLibrary, MusicBrainz, BGG, IGDB, TMDB).

### 4. Egzemplarz (F4): Przedmiot w Twoich rękach

**Egzemplarz** to pojedynczy fizyczny egzemplarz danej Manifestacji — konkretny przedmiot stojący na Twoim regale lub leżący na biurku.

* **Przykłady:** *Twój* egzemplarz książki — ten ze śladem po kawie na 42. stronie, Twoim osobistym ekslibrisem i kodem QR na wewnętrznej stronie okładki.

* **Dlaczego ma to znaczenie:** Przyjacielowi nie pożyczasz abstrakcyjnego numeru „ISBN”, lecz *swój własny egzemplarz*. Prywatność, historia wypożyczeń, data zakupu, cena i lokalizacja na półce są rejestrowane właśnie na poziomie Egzemplarza.

---

## Uniwersalność iqoqo: Daleko poza książki

Dzięki rozdzieleniu *abstrakcyjnej twórczości* od *fizycznego nośnika*, iqoqo nie ogranicza się wyłącznie do książek. Tradycyjna aplikacja do książek zawodzi, gdy próbujesz skatalogować płytę winylową czy puzzle, ponieważ jej baza jest na sztywno zaprojektowana pod pola \`Autor\`, \`Strony\` i \`ISBN\`.

W iqoqo ontologia dopasowuje się naturalnie do całego Twojego życia kulturalnego:

| Kategoria mediów | Dzieło (F1) | Ekspresja (F2) | Manifestacja (F3) | Egzemplarz (F4) |
| :--- | :--- | :--- | :--- | :--- |
| **Książki i komiksy** | Powieść / Komiks | Tekst oryginału, Przekład, Wydanie ilustrowane | Twarda oprawa, Wydanie kieszonkowe, ePub (ISBN) | Twój egzemplarz z autografem na półce B |
| **Muzyka i audio** | Album studyjny / Symfonia | Miks stereo 1973, Remaster 2023, Zapis koncertu | 2xLP Gatefold Vinyl, SACD, Cyfrowy FLAC | Twój japoński winyl w stanie idealnym |
| **Filmy i seriale** | Film pełnometrażowy / Miniserial | Wersja kinowa, Wersja reżyserska, Dubbing | Wydanie Combo 4K UHD + Blu-ray | Płyta w Twojej szafce RTV |
| **Gry planszowe** | Gra podstawowa / Dodatek | Zasady 1. edycji, Zasady 2. edycji | Wydanie sklepowe wielojęzyczne, Kickstarter Deluxe | Twoje pudełko (z własnym insertem 3D!) |
| **Gry wideo** | Tytuł gry | Wydanie premierowe, Edycja Gry Roku (GOTY) | Fizyczna płyta PS5, Kartridż Switch, Wersja Steam | Twój kartridż pożyczony znajomemu |
| **Puzzle** | Grafika / Ilustracja | Układ 1000 elementów, Wersja panoramiczna | Pudełko Ravensburger 2022 | Twoje pudełko (z brakującym 1 elementem!) |

---

## Codzienne supermoce dzięki modelowi FRBR

Nie musisz mieć doktoratu z bibliotekoznawstwa, aby korzystać z iqoqo — podczas skanowania kodu kreskowego system buduje to czteropoziomowe drzewo automatycznie w ułamku sekundy. Oto co zyskujesz na co dzień:

1. **Przejrzystość i maksymalny detal:** W widoku Kolekcji możesz zobaczyć wszystkie wydania zgrupowane elegancko pod jednym Dziełem lub przełączyć się, by sprawdzić każdy posiadany fizyczny egzemplarz.
2. **Sprytniejsza Lista Życzeń:** Dodając pozycję do Listy Życzeń, decydujesz o poziomie szczegółowości. Chcesz po prostu przeczytać *Diunę* w dowolnym wydaniu? Dodaj do listy **Dzieło**. Polujesz na konkretne pierwsze wydanie w twardej oprawie z 1965 roku? Dodaj dokładną **Manifestację**.
3. **Elastyczne Plany (Roadmaps):** W Planach czytania i grania możesz układać maratony, celując w abstrakcyjne Dzieła, konkretne przekłady, a nawet w konkretny Egzemplarz pożyczony od znajomego, który musisz oddać do piątku.
4. **Precyzyjne oceny i recenzje:** Przyznaj 5 gwiazdek **Dziełu**, bo historia lub mechanika gry są genialne, a jednocześnie wystaw 2 gwiazdki konkretnej **Manifestacji**, gdyż wydawca użył cienkiego papieru i kiepskiego kleju.
`,
    },
  },
  {
    slug: "camera-to-catalog",
    category: "tools",
    title: {
      en: "From Camera to Catalog: Scanning, Manual Entry & Curatorial Help",
      pl: "Od aparatu do katalogu: Skanowanie, ręczne dodawanie i pomoc kustoszy",
    },
    description: {
      en: "Learn how the scanner, batch mode, manual creation form, and curator escalations keep your library pristine.",
      pl: "Dowiedz się, jak skaner, tryb seryjny, formularz ręczny i zgłoszenia kustoszy dbają o Twój katalog.",
    },
    content: {
      en: `# From Camera to Catalog: Scanning, Manual Entry & Curatorial Help

Adding items to iqoqo is designed to be effortless when a barcode is handy—and forgiving when it isn't. Whether you are cataloging a stack of modern novels with crisp ISBN barcodes, a 1970s vinyl record with no barcode at all, or a bruised flea-market find, the Scanner adapts to what you have in front of you.

Here is the complete guide to how scanning works under the hood, how to handle edge cases manually, and how to summon Curators (or AI!) when you need a hand.

---

## 1. The Anatomy of a Scan: Mode vs. Intent

When you open the Scanner, you will notice two controls in the top bar before you even point your camera. Understanding how they work together will save you dozens of clicks:

![Scanner Mode, Intent, and Ingestion Flow](/images/help/scanner-workflow.jpg)

### Single vs. Batch Mode


* **Single Mode:** Best when you just bought one new book or game. You scan the barcode, review the rich success card, and jump straight to the new item's page.

* **Batch Mode:** Built for cataloging an entire bookshelf at once. Keep your phone in one hand and pull books off the shelf with the other—every time iqoqo recognizes a barcode, it chimes, shows a non-blocking toast card at the bottom of the screen, and **keeps the camera viewfinder active** so you can scan the next item immediately.

### Policy / Intent: Collection vs. Wishlist


* **Add to Collection (OWNED):** Creates a physical **Item (F4)** in your inventory and links it to the Manifestation.

* **Add to Wishlist (WISHLIST):** Bypasses physical Item creation and records your intent to acquire that **Manifestation (F3)** or **Work (F1)** in your Wishlist—perfect for when you are browsing a brick-and-mortar bookstore or board game shop!

---

## 2. When a Barcode Isn't Enough: Disambiguation & Manual Entry

Barcodes can be messy. Sometimes a publisher reuses an EAN barcode across three different board game printings, or an old book simply predates the invention of ISBNs in 1970.

### Step A: The Disambiguation Sheet

If your scan or title search returns multiple plausible matches across our upstream providers (OpenLibrary, Google Books, Allegro, BGG, Discogs, MusicBrainz, IGDB, TMDB), iqoqo slides up the **Disambiguation Sheet**.

* Compare cover thumbnails, publication years, publishers, and media badges (\`Book\`, \`Board Game\`, \`Vinyl\`, \`Video Game\`).

* Tap the exact edition you hold in your hands to bind it to your catalog.

### Step B: Going All the Way to Manual Entry

If an item is completely unknown to global databases—such as a local indie zine, a self-published chapbook, a bootleg concert recording, or a vintage puzzle—click **Add Manually** in the scanner bottom sheet:
1. **Select the Media Kind:** Choose whether you are adding a \`Book\`, \`Audio\`, \`Video\`, \`Board Game\`, \`Video Game\`, or \`Puzzle\`. The form dynamically adjusts its fields to match your medium!
2. **Enter Core Bibliographic Details:** Provide the Title, Creator/Author, Publisher, Publication Year, and Language.
3. **Dual-Source Cover Picker:** You don't have to leave your manual entry with a blank placeholder! Use the Cover Upload Picker right inside the form to either snap a live photo with your camera or pick an existing image file from your device.
4. **Save & Construct WEMI:** When you submit the form, iqoqo automatically constructs the full 4-tier FRBR hierarchy (Work -> Expression -> Manifestation -> Item) and applies your cover art.

---

## 3. Working with Curators: Escalations & Help Requests

Why can't regular users directly edit a book's title, change its author, or delete a Manifestation from the database?

Because of **FRBR!** Remember that while your **Item (F4)** belongs exclusively to you, the **Manifestation (F3)**, **Expression (F2)**, and **Work (F1)** are shared bibliographic records. If ten users on your instance own the same edition of *Dune*, and one user accidentally deletes the Manifestation or changes the author's name to a typo, it would corrupt the catalog for the other nine collectors.

Instead, iqoqo uses a collaborative **Curator Escalation System**:

### What You Can Do Yourself (Instant)


* Edit your **Item's** private notes, physical location/shelf, condition, purchase price, lending status, and visibility.

* Contribute a missing cover photo to a coverless Manifestation.

* Add or remove items from your personal Wishlist and Reading Roadmaps.

### When to Request Curator Help (Escalations)

On any Item, Manifestation, Expression, or Work page, click the **Request Curator Help / Report Issue** button in the action bar whenever you need to:
1. **Remove an Item or Duplicate Record (DELETION_REQUEST):** Need to remove a mistaken scan or delete an item from your inventory? Submit a deletion request—a Curator will verify whether only your F4 Item should be removed or if an orphaned F3 Manifestation should be cleaned up too.
2. **Fix Bibliographic Metadata (METADATA_FIX):** Spotted a typo in a title, a missing translator, the wrong publication year, or a book categorized as a board game? Flag it for a Curator, who can use the FRBR Editor or trigger a multi-provider metadata refetch.
3. **Merge Duplicates (DUPLICATE_REPORT):** Noticed two separate Work pages for the same novel? Let the Curators know so they can merge them cleanly in the Duplicate Reviewer.

> 💡 **Track Your Requests:** Open your **Requests** page (or check the Notification Center bell in the top navigation bar) to see real-time status updates and read resolution notes from your instance Curators!

---

## 4. For Administrators: Enabling AI Superpowers

If you are an **Instance Administrator**, you can supercharge both the Scanner and the Cover Art Editor by enabling optional AI integrations in Instance Settings (or via your \`.env\` configuration).

### 🔍 1. AI Vision Cover Scanning (Metadata Extraction)

When a user scans an antique book or a vinyl sleeve that has no barcode, they can snap a photo of the front cover in the Scanner.

* **How it works:** If AI Vision is enabled, iqoqo sends the cover image to your configured vision model—supporting **Local AI (Ollama / LLaVA)** for 100% offline privacy, **Google Gemini**, or **OpenAI**.

* **The Result:** The vision model reads the typography and layout on the cover, automatically extracting the Title, Author/Artist, Publisher, and Edition clues, pre-filling the manual entry pipeline.

### 🎨 2. AI Bespoke Cover Generation

What about Works that have *never* had a cover—like a digital-only fan translation or a classical symphony recording?

* **How it works:** In the Admin Cover Editor, administrators can enable LLM Cover Generation powered by Local AI, Google Gemini, or OpenAI.

* **The Result:** Using the Work's title, author, genre tags, and synopsis, iqoqo synthesizes a tasteful, high-resolution cover illustration—complete with automatic provenance metadata so users always know whether a cover is an original publisher scan, a user photo, or an AI-generated artwork!
`,
      pl: `# Od aparatu do katalogu: Skanowanie, ręczne dodawanie i pomoc kustoszy

Dodawanie pozycji do iqoqo zostało zaprojektowane tak, aby było błyskawiczne, gdy kod kreskowy jest pod ręką — i wyrozumiałe, gdy go brakuje. Niezależnie od tego, czy katalogujesz stos współczesnych powieści z czytelnymi kodami ISBN, płytę winylową z lat 70. bez żadnego kodu, czy książkę znalezioną na targu staroci, wbudowany Skaner dopasowuje się do tego, co trzymasz w rękach.

Oto kompletny przewodnik po działaniu skanowania, obsłudze nietypowych wydań oraz współpracy z Kustoszami (i modelami AI!).

---

## 1. Anatomia skanowania: Tryb a Intencja

Gdy otwierasz Skaner, na górnym pasku zobaczysz dwa przełączniki jeszcze przed skierowaniem kamery na kod. Zrozumienie ich działania zaoszczędzi Ci dziesiątki kliknięć:

![Przebieg skanowania, wybór trybu i obsługa wyników](/images/help/scanner-workflow.jpg)

### Tryb pojedynczy a Tryb seryjny (Batch)


* **Tryb pojedynczy:** Idealny, gdy kupujesz jedną nową książkę lub grę. Skanujesz kod, oglądasz kartę sukcesu i przechodzisz od razu do strony nowego egzemplarza.

* **Tryb seryjny (Batch):** Stworzony do katalogowania całego regału naraz. Trzymaj telefon w jednej ręce i zdejmuj książki z półki drugą — za każdym razem, gdy iqoqo rozpozna kod, wyda dźwięk potwierdzenia, wyświetli dyskretne powiadomienie na dole ekranu i **pozostawi aktywny podgląd kamery**, by od razu skanować kolejną pozycję.

### Intencja dodania: Półka czy Lista Życzeń


* **Dodaj do kolekcji (Na półkę):** Tworzy fizyczny **Egzemplarz (F4)** w Twoim inwentarzu i łączy go z wybraną Manifestacją.

* **Dodaj do Listy Życzeń:** Pomija tworzenie fizycznego przedmiotu i rejestruje chęć nabycia danej **Manifestacji (F3)** lub **Dzieła (F1)** na Twojej Liście Życzeń — idealne rozwiązanie, gdy przeglądasz półki w księgarni stacjonarnej!

---

## 2. Gdy kod kreskowy nie wystarcza: Ujednoznacznianie i formularz ręczny

Kody kreskowe bywają niejednoznaczne. Czasami wydawca używa tego samego kodu EAN dla trzech różnych dodruków gry planszowej, a starsze książki wydano przed wprowadzeniem systemu ISBN w 1970 roku.

### Krok A: Arkusz ujednoznaczniania (Disambiguation Sheet)

Jeśli skanowanie lub wyszukiwanie po tytule zwróci kilka prawdopodobnych dopasowań z zewnętrznych źródeł (OpenLibrary, Google Books, Allegro, BGG, Discogs, MusicBrainz, IGDB, TMDB), iqoqo wysunie **Arkusz ujednoznaczniania**.

* Porównaj miniatury okładek, lata wydania, wydawców i etykiety mediów (\`Książka\`, \`Gra planszowa\`, \`Winyl\`, \`Gra wideo\`).

* Dotknij dokładnie tego wydania, które trzymasz w dłoni, aby dołączyć je do swojej kolekcji.

### Krok B: Ręczne wprowadzanie danych

Jeśli pozycja jest zupełnie nieznana globalnym bazom — jak lokalny zin, tomik poezji wydany własnym sumptem czy unikatowe puzzle — kliknij **Wprowadź ręcznie** w dolnym panelu skanera:
1. **Wybierz rodzaj nośnika:** Określ, czy dodajesz \`Książkę\`, \`Muzykę\`, \`Wideo\`, \`Grę planszową\`, \`Grę wideo\` czy \`Puzzle\`. Formularz dynamicznie dopasuje pola do Twojego wyboru!
2. **Wprowadź podstawowe dane bibliograficzne:** Podaj tytuł, autora/twórcę, wydawcę, rok wydania i język.
3. **Dodaj okładkę:** Nie musisz zostawiać pustego szarego pola! Skorzystaj z przełącznika źródła okładki, aby zrobić zdjęcie aparatem lub wybrać plik graficzny z pamięci urządzenia.
4. **Zapisz i zbuduj drzewo WEMI:** Po zatwierdzeniu formularza iqoqo automatycznie zbuduje pełną hierarchię FRBR (Dzieło -> Ekspresja -> Manifestacja -> Egzemplarz) wraz z okładką.

---

## 3. Współpraca z Kustoszami: Zgłoszenia i prośby o pomoc

Dlaczego zwykły użytkownik nie może bezpośrednio zmienić tytułu książki, poprawić nazwiska autora lub usunąć Manifestacji z bazy?

Wynika to z **modelu FRBR!** Pamiętaj, że o ile Twój **Egzemplarz (F4)** należy wyłącznie do Ciebie, o tyle **Manifestacja (F3)**, **Ekspresja (F2)** i **Dzieło (F1)** są wspólnymi rekordami bibliograficznymi. Jeśli dziesięciu użytkowników na Twojej instancji posiada to samo wydanie *Diuny*, a jeden z nich omyłkowo zmieniłby autora na literówkę lub usunął wydanie, uszkodziłoby to katalog pozostałym dziewięciu kolekcjonerom.

Dlatego iqoqo stosuje **System Zgłoszeń do Kustoszy**:

### Co możesz zrobić samodzielnie (natychmiast)


* Edytować prywatne notatki, półkę/lokalizację, stan zachowania, cenę zakupu, status wypożyczenia i widoczność **Egzemplarza**.

* Dodać brakujące zdjęcie okładki do Manifestacji.

* Dodawać i usuwać pozycje ze swojej Listy Życzeń oraz Planów czytania.

### Kiedy poprosić Kustosza o pomoc

Na stronie dowolnego Egzemplarza, Manifestacji, Ekspresji lub Dzieła kliknij przycisk **Zgłoś problem / Poproś kustosza**, gdy chcesz:
1. **Usunąć rekord lub błędny skan:** Chcesz skasować błędnie dodany rekord? Wyślij prośbę — Kustosz zweryfikuje, czy usunąć tylko Twój egzemplarz, czy także osieroconą Manifestację.
2. **Poprawić metadane bibliograficzne:** Zauważyłeś literówkę w tytule, brakującego tłumacza lub błędny rok wydania? Zgłoś to Kustoszowi, który poprawi wpis w Edytorze FRBR lub pobierze świeże dane od dostawców.
3. **Połączyć duplikaty:** Widzisz dwa osobne Dzieła dla tej samej powieści? Daj znać Kustoszom, aby połączyli je w module deduplikacji.

> 💡 **Śledź swoje zgłoszenia:** Wejdź na stronę **Zgłoszenia** w menu użytkownika (lub kliknij ikonę dzwonka w powiadomieniach), aby w czasie rzeczywistym widzieć status rozpatrzenia i notatki kustosza!

---

## 4. Dla Administratorów: Włączanie funkcji AI

Jako **Administrator instancji** możesz wzbogacić Skaner oraz Edytor okładek o opcjonalne integracje sztucznej inteligencji w Ustawieniach instancji.

### 🔍 1. Skanowanie okładek za pomocą AI Vision

Gdy użytkownik skanuje starodruk lub płytę winylową bez kodu kreskowego, może zrobić zdjęcie samej okładki.

* **Jak to działa:** Jeśli AI Vision jest włączone, iqoqo przesyła obraz do skonfigurowanego modelu wizyjnego — obsługując **Lokalne AI (Ollama / LLaVA)** z gwarancją 100% prywatności offline, **Google Gemini** lub **OpenAI**.

* **Efekt:** Model odczytuje typografię z okładki, automatycznie wyodrębniając tytuł, autora, wydawcę oraz wskazówki dotyczące wydania, oszczędzając ręcznego wpisywania.

### 🎨 2. Generowanie dedykowanych okładek AI

A co z dziełami, które nigdy nie miały fizycznej okładki — jak cyfrowe tłumaczenia fanowskie czy nagrania archiwalne?

* **Jak to działa:** W Edytorze okładek administrator może włączyć generator okładek oparty o modele LLM.

* **Efekt:** Na podstawie tytułu, autora, gatunku i opisu iqoqo generuje estetyczną ilustrację okładkową w wysokiej rozdzielczości — z pełną metadaną proweniencji, dzięki czemu użytkownicy zawsze wiedzą, czy okładka pochodzi od wydawcy, ze zdjęcia użytkownika, czy z generacji AI!
`,
    },
  },
  {
    slug: "privacy-sharing-social",
    category: "privacy",
    title: {
      en: "Privacy, Sharing & Social Interactions: The Hidden Gems",
      pl: "Prywatność, udostępnianie i funkcje społecznościowe: Ukryte perełki",
    },
    description: {
      en: "Discover three-tier cascading visibility, tokenized filtered collection links, notes, and local barcodes.",
      pl: "Poznaj trójstopniową widoczność kaskadową, tokenizowane linki do kolekcji, notatki i lokalne kody.",
    },
    content: {
      en: `# Privacy, Sharing & Social Interactions: The Hidden Gems

At first glance, iqoqo looks like a serene, personal catalog for your media. Dig a little deeper, however, and you will find a rich layer of privacy controls, granular sharing tools, and multi-tier social interactions designed for families, collector clubs, and federated friends.

Because iqoqo is built on a **"Privacy by Default"** philosophy, many of these capabilities stay politely out of your way until you need them. Here is your guide to the social and privacy features—especially the non-obvious ones tucked beneath the surface.

---

## 1. The Three-Tier Privacy Model (And How Cascading Works)

In iqoqo, visibility is never an all-or-nothing switch. We separate **who you are** from **what you own**, using three visibility levels:
* 🔒 **PRIVATE:** Visible only to you (and instance Custody Admins for inventory maintenance).

* 👥 **FRIENDS_ONLY:** Visible to accepted followers/friends (both local and federated, if you opted into federation).

* 🌍 **PUBLIC:** Visible to anyone visiting your instance or querying the public Semantic Web endpoints.

![Three-Tier Privacy and Cascading Visibility Gate](/images/help/privacy-cascading-model.jpg)

### 💡 Non-Obvious Detail: Default vs. Per-Item Overrides

In your Profile Settings, you set your **Default Item Visibility** (which defaults to \`PRIVATE\`). Every time you scan a batch of books in the Scanner, they inherit this default.

* **The Hidden Gem:** What if your collection is mostly \`PUBLIC\`, but you just bought a rare, expensive first-edition comic—or a guilty-pleasure book—that you don't want anyone to see? Or what if your collection is \`PRIVATE\`, but you want to show off *one specific* board game to your friends?

* **How to do it:** Open that specific Item's detail page, click **Edit Item**, and change its individual **Visibility** dropdown. Per-item visibility always overrides your account default!

---

## 2. Sharing Filtered Collection Views (Tokenized Share Links)

You don't have to make your entire profile public just to show a friend which board games you can bring to game night!

### How Snapshot / Filter Sharing Works

When you are browsing your Collection, every filter you apply in the sidebar—such as \`Media: Board Games\`, \`Players: 4\`, \`Tag: Co-op\`, and \`On Shelf: Yes\`—is synchronized in real time with the page URL.

If you click the **Share Collection** button in the top toolbar:
1. **Secret Token Generation:** iqoqo generates a cryptographically random, unguessable share link (\`/share/[token]\`).
2. **Scoped Visibility:** Anyone with that link can view **only** the items that match the exact filter combination you had active when you created the link—even if your profile is otherwise private!
3. **Clean Guest UI:** Visitors opening a share link see a streamlined, read-only gallery. Personal management buttons, acquisition prices, and private notes are automatically stripped out.
4. **Instant Revocation:** Changed your mind? You can revoke active share tokens at any time from your sharing settings, immediately invalidating the URL.

---

## 3. Multi-Tier Comments, Ratings & Private Notes

In most apps, a "comment" or "note" box is just a single text field. In iqoqo, where you leave a note determines **what it means** and **who can see it**:

### ⭐ Star Ratings & Public Reviews (Work / Expression / Manifestation)

When you rate or review a **Work**, **Expression**, or **Manifestation**:
* You are contributing to the **community critical reception** of that creation.

* **Non-Obvious Nuance:** Rate the **Work** to judge the author's story or the game designer's rules. Rate the **Expression** to judge the translator or audiobook narrator. Rate the **Manifestation** to judge the physical build quality (e.g., *"The binding on this 2021 hardcover falls apart!"*).

### 📝 Private & Social Notes

Every FRBR page features a dedicated **Notes** section. Unlike public reviews, Notes are designed for your personal marginalia—reading quotes, house rules for a board game, or reminders about who recommended a record to you.

* You can toggle individual notes between **Private** (strictly for your eyes only) and **Shared**, allowing you to keep personal study notes right alongside public discussions without mixing them up.

---

## 4. "Check Inventory" & Multi-Owner Households

If you use iqoqo with your partner, family, or a local club on the same instance, you might wonder: *"Do we already own a copy of this book in the house?"*


* **The Hidden Gem:** On any public Work or Manifestation page, look for the **Check Inventory / Custody & Owners** panel.

* **How it works:** Instead of duplicating the bibliographic record, iqoqo links every household member's physical copy (F4 Item) to the same Manifestation (F3). At a glance, you can see that **2 copies** exist on the instance: one owned by you (*On Shelf*), and one owned by your partner (*Lent Out*).

* **Self-Borrowing & Custody:** If an item is owned by a shared household or club account, you can use the **Borrow / Lending** action on the Item sidebar to check it out to yourself, updating its real-time custody without changing its legal owner!

---

## 5. QR Code Inventory Labels & Local Barcodes

What do you do with items that never had a barcode in the first place—like a 1960s sci-fi paperback, a handmade zine, or a custom-printed board game expansion? Or what if you own **three identical copies** of the same book and need to tell them apart when lending them out?

1. **Local Inventory Barcodes:** Every Item in iqoqo can be assigned a unique **Local Barcode / Inventory Tag** in the Item Editor.
2. **Printable QR Labels:** Open any Item's detail page and click the **QR Code** button in the sidebar. iqoqo generates a high-contrast, printable QR label containing the item's canonical identifier and title.
3. **Instant Scan-to-Item Resolution:** Stick that QR code inside the book cover or on the side of the board game box. Next time you open the Scanner and point your camera at that QR code, iqoqo bypasses external metadata lookups and jumps **directly to your exact physical copy**—ready for you to lend it out, mark it returned, or update its reading status!
`,
      pl: `# Prywatność, udostępnianie i funkcje społecznościowe: Ukryte perełki

Na pierwszy rzut oka iqoqo wygląda jak spokojny, osobisty katalog Twoich zbiorów. Wystarczy jednak zajrzeć nieco głębiej, aby odkryć bogaty zestaw narzędzi ochrony prywatności, precyzyjne mechanizmy udostępniania oraz wielopoziomowe funkcje społecznościowe stworzone z myślą o rodzinach, klubach kolekcjonerskich i sieci znajomych w federacji.

Ponieważ iqoqo opiera się na filozofii **„Domyślnej ochrony prywatności” (Privacy by Default)**, wiele z tych możliwości pozostaje dyskretnie w tle, dopóki ich nie potrzebujesz. Oto przewodnik po funkcjach społecznościowych i ustawieniach prywatności — zwłaszcza tych mniej oczywistych.

---

## 1. Trójstopniowy model prywatności (i kaskadowe dziedziczenie)

W iqoqo widoczność nigdy nie jest prostym przełącznikiem „wszystko albo nic”. Rozdzielamy **to, kim jesteś** od **tego, co posiadasz**, stosując trzy poziomy widoczności:
* 🔒 **PRYWATNY (PRIVATE):** Widoczny wyłącznie dla Ciebie (oraz administratorów instancji w celach inwentarzowych).

* 👥 **DLA ZNAJOMYCH (FRIENDS_ONLY):** Widoczny dla zaakceptowanych znajomych (zarówno lokalnych, jak i w federacji, jeśli włączono zgodę federacyjną).

* 🌍 **PUBLICZNY (PUBLIC):** Widoczny dla każdego odwiedzającego Twoją instancję oraz dostępny przez publiczne punkty Semantic Web.

![Trójstopniowy model prywatności i kaskadowa bramka uprawnień](/images/help/privacy-cascading-model.jpg)

### 💡 Nieoczywisty detal: Domyślna widoczność a nadpisywanie dla pojedynczego egzemplarza

W Ustawieniach profilu określasz **Domyślną widoczność egzemplarzy** (domyślnie: \`PRYWATNY\`). Każda nowo zeskanowana partia książek w Skanerze dziedziczy to ustawienie.

* **Ukryta perełka:** Co jeśli Twoja kolekcja jest w większości publiczna, ale kupiłeś właśnie rzadki, drogi komiks lub książkę, którą wolisz zachować tylko dla siebie? Albo Twoja kolekcja jest prywatna, lecz chcesz pochwalić się znajomym *tą jedną konkretną* grą planszową?

* **Jak to zrobić:** Otwórz stronę danego Egzemplarza, kliknij **Edytuj egzemplarz** i zmień pole **Widoczność**. Ustawienie konkretnego egzemplarza zawsze ma pierwszeństwo przed domyślnym ustawieniem konta!

---

## 2. Udostępnianie przefiltrowanych widoków (Tokenizowane linki)

Nie musisz upubliczniać całego profilu tylko po to, by pokazać znajomym, jakie gry planszowe możesz zabrać na piątkowe spotkanie!

### Jak działa udostępnianie przefiltrowanych widoków

Gdy przeglądasz Kolekcję, każdy filtr zastosowany w panelu bocznym — np. \`Media: Gry planszowe\`, \`Liczba graczy: 4\`, \`Tag: Kooperacja\`, \`Na półce: Tak\` — synchronizuje się w czasie rzeczywistym z adresem URL.

Klikając przycisk **Udostępnij kolekcję** na górnym pasku:
1. **Generowanie unikalnego tokenu:** iqoqo tworzy bezpieczny, kryptograficzny odnośnik (\`/share/[token]\`).
2. **Ściśle ograniczony zasięg:** Każdy, kto otworzy ten link, zobaczy **wyłącznie** pozycje spełniające dokładnie te kryteria, które były aktywne w chwili generowania linku — nawet jeśli Twój profil jest w pełni prywatny!
3. **Czysty interfejs gościa:** Osoba odwiedzająca widzi przejrzystą galerię tylko do odczytu. Przyciski zarządzania, ceny zakupu i prywatne notatki są automatycznie ukrywane.
4. **Natychmiastowe unieważnienie:** Zmieniłeś zdanie? W każdej chwili możesz cofnąć aktywny token w ustawieniach udostępniania, natychmiast wyłączając dostęp.

---

## 3. Wielopoziomowe recenzje, oceny i notatki

W typowych aplikacjach pole na notatkę to po prostu zwykły edytor tekstu. W iqoqo to, gdzie zostawiasz wpis, decyduje o **jego znaczeniu** i **odbiorcach**:

### ⭐ Oceny gwiazdkowe i publiczne recenzje (Dzieło / Ekspresja / Manifestacja)

Gdy oceniasz lub recenzujesz **Dzieło**, **Ekspresję** lub **Manifestację**:
* Współtworzysz **społecznościowy odbiór krytyczny** danego utworu.

* **Ważny niuans:** Oceń **Dzieło**, by docenić kunszt pisarza lub mechanikę projektanta gry. Oceń **Ekspresję**, by ocenić pracę tłumacza lub lektora audiobooka. Oceń **Manifestację**, by ocenić jakość wydania (np. *„W tym wydaniu z 2021 roku klej w grzbiecie puszcza po tygodniu!”*).

### 📝 Notatki prywatne i współdzielone

Każda strona w modelu FRBR posiada dedykowaną sekcję **Notatki**. W przeciwieństwie do publicznych recenzji, notatki służą do zapisywania Twoich osobistych zapisków na marginesie — cytatów, zasad domowych w grze czy informacji, kto polecił Ci daną płytę.

* Możesz oznaczać notatki jako **Prywatne** (tylko dla Ciebie) lub **Współdzielone**, co pozwala trzymać osobiste zapiski obok dyskusji bez ich przypadkowego wymieszania.

---

## 4. Panel „Sprawdź zbiory” w gospodarstwach domowych

Jeśli korzystasz z iqoqo z partnerem, rodziną lub klubem na tej samej instancji, zapewne nie raz padło pytanie: *„Czy my przypadkiem nie mamy już tej książki w domu?”*


* **Ukryta perełka:** Na stronie dowolnego publicznego Dzieła lub Manifestacji spójrz na panel **Sprawdź zbiory / Posiadacze**.

* **Jak to działa:** Zamiast duplikować rekord bibliograficzny, iqoqo łączy fizyczne egzemplarze (F4) wszystkich domowników z tą samą Manifestacją (F3). Od razu widzisz, że na instancji znajdują się **2 egzemplarze**: jeden Twój (*Na półce*), a drugi Twojego partnera (*Wypożyczony znajomemu*).

* **Wypożyczenia wewnątrz instancji:** Jeśli egzemplarz należy do wspólnego konta domowego lub klubowego, możesz skorzystać z akcji wypożyczenia, aby przypisać sobie pieczę nad egzemplarzem bez zmiany jego właściciela prawnego!

---

## 5. Etykiety z kodami QR i lokalne kody inwentarzowe

Co zrobić z pozycjami, które nigdy nie miały fabrycznego kodu kreskowego — jak powieść z lat 60., ręcznie robiony zin czy dodatek do gry wydrukowany na drukarce 3D? Albo gdy masz **trzy identyczne egzemplarze** tej samej książki i chcesz je bezbłędnie rozróżniać podczas wypożyczania?

1. **Lokalne kody kreskowe:** Każdemu Egzemplarzowi w iqoqo możesz nadać własny kod inwentarzowy w Edytorze egzemplarza.
2. **Drukowalne etykiety QR:** Otwórz stronę Egzemplarza i kliknij przycisk **Kod QR** w panelu bocznym. iqoqo wygeneruje czytelną etykietę z kodem QR zawierającą tytuł i unikalny identyfikator.
3. **Natychmiastowe rozpoznawanie w Skanerze:** Naklej kod QR wewnątrz okładki lub na pudełku z grą. Następnym razem, gdy skierujesz aparat Skanera na ten kod, iqoqo pominie przeszukiwanie zewnętrznych baz i otworzy **dokładnie Twój fizyczny egzemplarz** — gotowy do oznaczenia wypożyczenia lub zmiany statusu czytania!
`,
    },
  },
  {
    slug: "federation-architecture",
    category: "federation",
    title: {
      en: "The iqoqo Federation: Connected Libraries, Sovereign Data",
      pl: "Federacja iqoqo: Połączone biblioteki, suwerenne dane",
    },
    description: {
      en: "Learn how independent iqoqo instances connect via ActivityPub S2S, cryptographic trust, and federated lending.",
      pl: "Poznaj zasady łączenia niezależnych instancji przez ActivityPub S2S, zaufanie kryptograficzne i wypożyczenia.",
    },
    content: {
      en: `# The iqoqo Federation: Connected Libraries, Sovereign Data

Traditional cataloging platforms force you into a painful trade-off:
* **Cloud Silos** (like Goodreads or BoardGameGeek) make it easy to see what your friends are reading and share community metadata, but they lock your data inside a corporate walled garden, track your habits, and can shut down or change their terms at any time.

* **Self-Hosted Apps** give you total ownership of your database, but leave you on a lonely digital island—cut off from your friends' collections and forced to curate every piece of metadata alone.

**iqoqo gives you both.** Through **Federation**, every independent iqoqo server (instance) can connect to a global, decentralized network of collectors, libraries, and curators—while you retain 100% sovereignty over your data.

![The iqoqo Federation: Connected Libraries, Sovereign Data](/images/help/federation-overview.jpg)

---

## Part 1: What Federation Gives You (For Everyday Users)

Think of iqoqo Federation like email or Mastodon. Your account lives on your home instance (for example, \`@anna@books.gdansk.pl\`), while your friend might host their own family instance at \`@marek@home-shelf.org\`. Because both servers speak the same open federation protocol, you can interact as if you were on the same website.

### 1. Follow Friends Across Instances

You can follow collectors on any trusted iqoqo instance. Once your follow request is accepted:
* Browse their public and **Friends-Only** shelves right from your own dashboard.

* Discover new books, vinyl records, and board games through their ratings and reviews.

* Toggle your dashboard insights between **My Collection**, **Instance**, and **Friends** scopes.

### 2. Cross-Instance Book & Game Lending

Have you ever lent a board game or a hardcover book to a friend who uses a different server, only for both of you to forget who has it six months later?

* With iqoqo, you can initiate a **Federated Loan** directly to a remote friend (\`@user@remote-instance.org\`).

* Your friend receives an interactive notification in their **Notification Center** to accept custody of the Item.

* While the item is lent out, it appears on your friend's shelf as a borrowed item (so they can add it to their Reading Roadmap!) while remaining marked as **"Lent Out"** in your inventory until you both confirm its return.

### 3. Shared Curatorial Wisdom (Federated Metadata Sync)

When a skilled curator on a trusted partner instance spends twenty minutes perfecting the FRBR tree for a rare sci-fi anthology or a multi-disc vinyl box set—linking it to Wikidata and uploading a crisp cover scan—your instance benefits automatically!

* Connected instances share **public bibliographic metadata** (Works, Expressions, Manifestations, Series, and LOD links).

* When you scan a barcode that your local server hasn't seen before, iqoqo can pull the richly curated FRBR record from the federation trust graph in seconds.

### 4. The Federation Directory (Index Instances)

Not sure which instances are out there? Visit the [Federation Directory](/federation/directory) to browse known peer instances in the network, see their public catalog statistics, and discover communities dedicated to specific niches (like vintage RPGs, classical vinyl, or neighborhood book swaps).

### 5. Privacy-First: The Federation Consent Gate

**Your data never leaves your server without your explicit permission.** 
* Even if your instance administrator enables federation, your personal profile, collection, and social activity are **never** federated by default.

* To participate in cross-instance social features or lending, you must explicitly opt in via your Profile Settings (**Federation Consent**). You can revoke this consent at any time.

---

## Part 2: Under the Hood (Technical Architecture)

For system administrators, self-hosters, and curious developers, iqoqo's federation is built on open W3C Semantic Web standards rather than proprietary APIs. It combines **ActivityPub (Server-to-Server)**, **WebFinger**, **HTTP Signatures**, **JSON-LD / RDF**, and **Federated SPARQL**.

![ActivityPub S2S Discovery and Cryptographic Loan Handshake](/images/help/federation-s2s-handshake.jpg)

### 1. Actor Discovery & WebFinger

Every federated user—and the instance itself—is represented as an **ActivityPub Actor** (\`Person\` or \`Application\`).

* When you look up \`@user@domain.tld\`, iqoqo queries \`/.well-known/webfinger\` on the target domain to resolve the canonical Actor IRI.

* Instance-level metadata and capabilities are exposed via \`/.well-known/nodeinfo\`.

### 2. Cryptographic Trust: RSA-2048 & HTTP Signatures

Every Server-to-Server (S2S) POST request sent to a remote inbox is cryptographically signed using **HTTP Signatures (draft-cavage)** with **RSA-SHA256** (2048-bit keys managed per actor/instance):
* Signed headers include \`(request-target)\`, \`host\`, \`date\`, and \`digest\` (SHA-256 hash of the JSON-LD body).

* **Replay & Clock-Skew Protection:** Incoming requests with a \`Date\` header skewed by more than ±300 seconds (5 minutes) from UTC are automatically rejected.

* **SSRF & DNS Rebinding Guard:** All outbound federation requests pass through a strict network guard (\`federation_guard\`) that blocks private IPv4/IPv6 ranges (\`127.0.0.0/8\`, \`10.0.0.0/8\`, \`169.254.0.0/16\`, \`::1\`, etc.) to prevent Server-Side Request Forgery.

### 3. Asynchronous Inbox / Outbox Pipeline

Federation network traffic never blocks the main web application:
* Outbound activities (\`Follow\`, \`Accept\`, \`Reject\`, \`Offer\`, \`Return\`, \`Create\`, \`Update\`, \`Delete\`) are queued to **Celery workers** backed by Redis with exponential backoff retries.

* Incoming activities hit \`/api/federation/inbox\`, where signatures and trust policies are verified before dispatching to domain handlers.

### 4. Canonical IRI Immutability & Tombstones

In a decentralized graph, changing an entity's URL breaks links across the entire network.

* Every FRBR entity (\`Work\`, \`Expression\`, \`Manifestation\`, \`Item\`) is assigned a **Canonical IRI** at creation time. Even if a local admin changes the instance's base domain name later, iqoqo preserves canonical IRI immutability and serves cryptographic domain-migration proofs.

* When an entity is deleted or merged, iqoqo emits an ActivityStreams \`Tombstone\` object (\`410 Gone\` or \`301 Moved Permanently\` for merges) so remote instances can cleanly update their local caches.

### 5. Trust Graph & Federated Metadata Sync

Instance administrators manage peer relationships in the Admin Federation Dashboard:
* **Trust Policies:** Peers can be set to \`TRUSTED\`, \`LIMITED\`, or \`BLOCKED\` (defederated).

* **Bibliographic Sync:** Trusted instances periodically exchange public F1/F2/F3 RDF graphs. To prevent remote spoofing, incoming graphs are validated against our **SHACL shapes**, and local curator locks always take precedence over remote updates.

### 6. Access-Controlled Federated SPARQL

Each instance runs an isolated **Oxigraph-powered SPARQL Execution Service**. When federated queries are executed across instances, iqoqo enforces strict **Federated Access Rights**: public queries only ever see public triples (Works, Expressions, Manifestations, and explicitly public Items), ensuring private and friends-only items are never leaked through graph traversal.
`,
      pl: `# Federacja iqoqo: Połączone biblioteki, suwerenne dane

Tradycyjne platformy do katalogowania stawiają użytkowników przed bolesnym kompromisem:
* **Silosy chmurowe** (jak Goodreads czy BoardGameGeek) ułatwiają podglądanie tego, co czytają znajomi i wymianę metadanych, ale zamykają Twoje dane w korporacyjnym ogrodzie, śledzą nawyki i mogą w każdej chwili zmienić regulamin lub zamknąć usługę.

* **Aplikacje instalowane lokalnie (self-hosted)** dają pełną własność nad bazą danych, ale zostawiają Cię na samotnej cyfrowej wyspie — odciętym od zbiorów przyjaciół i zmuszonym do samodzielnego wpisywania każdej informacji.

**iqoqo łączy zalety obu światów.** Dzięki **Federacji** każdy niezależny serwer (instancja) iqoqo może łączyć się w globalną, zdecentralizowaną sieć kolekcjonerów, bibliotek i kustoszy — podczas gdy Ty zachowujesz 100% suwerenności nad swoimi danymi.

![Federacja iqoqo: Połączone biblioteki i suwerenność danych](/images/help/federation-overview.jpg)

---

## Część 1: Co daje Federacja (Dla codziennych użytkowników)

Pomyśl o Federacji w iqoqo jak o poczcie e-mail lub sieci Mastodon. Twoje konto żyje na Twojej domowej instancji (na przykład \`@anna@ksiazki.gdansk.pl\`), podczas gdy Twój znajomy prowadzi własny serwer rodzinny pod adresem \`@marek@domowa-polka.pl\`. Ponieważ oba serwery posługują się tym samym protokołem, możecie wchodzić w interakcje tak, jakbyście korzystali z tej samej strony.

### 1. Obserwowanie znajomych między instancjami

Możesz obserwować kolekcjonerów na dowolnej zaufanej instancji iqoqo. Gdy Twoja prośba o obserwację zostanie zaakceptowana:
* Przeglądasz ich półki publiczne oraz **Tylko dla znajomych** bezpośrednio ze swojego pulpitu.

* Odkrywasz nowe książki, płyty winylowe i gry planszowe dzięki ich ocenom i recenzjom.

* Przełączasz statystyki na pulpicie między widokiem **Moja kolekcja**, **Instancja** oraz **Znajomi**.

### 2. Wypożyczanie książek i gier między serwerami

Czy zdarzyło Ci się pożyczyć grę planszową lub książkę znajomemu, a po pół roku żaden z Was nie pamiętał, u kogo się znajduje?

* W iqoqo możesz zainicjować **Wypożyczenie federacyjne** bezpośrednio do zdalnego znajomego (\`@user@zdalna-instancja.pl\`).

* Znajomy otrzymuje interaktywne powiadomienie w swoim **Centrum Powiadomień**, aby potwierdzić odbiór przedmiotu.

* Na czas wypożyczenia przedmiot pojawia się na półce znajomego jako pozycja pożyczona (może dodać ją do swojego Planu czytania!), pozostając jednocześnie oznaczona jako **„Pożyczona komuś”** w Twoim inwentarzu, dopóki oboje nie potwierdzicie zwrotu.

### 3. Wspólna wiedza kustoszy (Synchronizacja metadanych)

Gdy zaangażowany kustosz na zaufanej partnerskiej instancji spędzi dwadzieścia minut na dopracowywaniu drzewa FRBR dla rzadkiej antologii science-fiction — łącząc ją z Wikidanymi i wgrywając skan okładki — Twoja instancja korzysta z tego automatycznie!

* Połączone instancje wymieniają się **publicznymi metadanymi bibliograficznymi** (Dzieła, Ekspresje, Manifestacje, Serie).

* Gdy skanujesz kod kreskowy, którego Twój lokalny serwer jeszcze nie widział, iqoqo może w kilka sekund pobrać dopracowany rekord z sieci zaufanych instancji.

### 4. Katalog instancji (Federation Directory)

Nie wiesz, jakie biblioteki działają w sieci? Odwiedź [Katalog połączonych bibliotek](/federation/directory), aby przejrzeć zarejestrowane węzły, sprawdzić ich statystyki publiczne i odkryć społeczności poświęcone niszowym zbiorom (jak klasyczne RPG czy płyty winylowe).

### 5. Zgoda na federację (Federation Consent Gate)

**Twoje dane nigdy nie opuszczają Twojego serwera bez Twojej wyraźnej zgody.**

* Nawet jeśli administrator włączy federację na serwerze, Twój profil, kolekcja i aktywność społecznościowa są **domyślnie całkowicie prywatne**.

* Aby uczestniczyć w wymianie czy wypożyczeniach między instancjami, musisz świadomie wyrazić zgodę w Ustawieniach profilu (**Zgoda na federację**). Możesz ją wycofać w dowolnej chwili.

---

## Część 2: Pod maską (Architektura techniczna)

Dla administratorów i ciekawskich programistów: federacja w iqoqo opiera się na otwartych standardach W3C Semantic Web: **ActivityPub (Server-to-Server)**, **WebFinger**, **HTTP Signatures**, **JSON-LD / RDF** oraz **Federated SPARQL**.

![Odkrywanie aktorów ActivityPub i kryptograficzny uścisk dłoni przy wypożyczeniu](/images/help/federation-s2s-handshake.jpg)

### 1. Odkrywanie tożsamości (WebFinger)

Każdy użytkownik w federacji jest reprezentowany jako **Aktor ActivityPub** (\`Person\` lub \`Application\`).

* Gdy wyszukujesz adres \`@user@domena.pl\`, iqoqo odpytuje endpoint \`/.well-known/webfinger\` na docelowej domenie, uzyskując kanoniczny identyfikator IRI Aktora.

* Metadane instancji i obsługiwane wersje protokołów są udostępniane przez \`/.well-known/nodeinfo\`.

### 2. Zaufanie kryptograficzne: RSA-2048 i HTTP Signatures

Każde zapytanie POST przesyłane między serwerami (S2S) jest podpisywane kryptograficznie przy użyciu **HTTP Signatures (draft-cavage)** z kluczem **RSA-SHA256** (2048-bitowe klucze zarządzane dla każdego aktora):
* Podpisywane nagłówki obejmują \`(request-target)\`, \`host\`, \`date\` oraz \`digest\` (skrót SHA-256 z treści JSON-LD).

* **Ochrona przed atakami powtórzeniowymi:** Zapytania z nagłówkiem \`Date\` różniącym się od czasu UTC o więcej niż ±300 sekund (5 minut) są natychmiast odrzucane.

* **Ochrona przed SSRF i DNS Rebinding:** Cały wychodzący ruch federacyjny przechodzi przez moduł \`federation_guard\`, który blokuje prywatne zakresy adresów IP (\`127.0.0.0/8\`, \`10.0.0.0/8\`, \`::1\` itd.).

### 3. Asynchroniczny potok Inbox / Outbox

Ruch sieciowy federacji nigdy nie blokuje głównej aplikacji internetowej:
* Wychodzące aktywności (\`Follow\`, \`Accept\`, \`Reject\`, \`Offer\`, \`Return\`, \`Create\`, \`Update\`, \`Delete\`) trafiają do **kolejki Celery** opartej na Redis z automatycznym ponawianiem prób.

* Przychodzące komunikaty trafiają na endpoint \`/api/federation/inbox\`, gdzie po weryfikacji podpisu są przekazywane do odpowiednich procesorów domenowych.

### 4. Niezmienne kanoniczne identyfikatory IRI i Tombstones

W grafie zdecentralizowanym zmiana adresu encji zrywa relacje w całej sieci.

* Każda encja FRBR otrzymuje **niezmienny kanoniczny IRI** w momencie utworzenia. Nawet jeśli administrator zmieni w przyszłości domenę serwera, iqoqo zachowuje tożsamość encji.

* Po usunięciu lub scaleniu encji iqoqo emituje obiekt ActivityStreams \`Tombstone\` (\`410 Gone\` lub \`301 Moved Permanently\`), dzięki czemu zdalne instancje aktualizują swoje lokalne pamięci podręczne.

### 5. Reguły zaufania i ochrona kształtów SHACL

Administratorzy zarządzają partnerami w Panelu Administracyjnym Federacji:
* Instancje mogą mieć status \`TRUSTED\` (zaufana), \`LIMITED\` (ograniczona) lub \`BLOCKED\` (zablokowana).

* Przychodzące grafy RDF od zaufanych partnerów są walidowane pod kątem zgodności z **kształtami SHACL**, a lokalne blokady kustoszy zawsze mają pierwszeństwo przed zdalnymi aktualizacjami.

### 6. Kontrola dostępu w SPARQL

Każda instancja uruchamia wyizolowany silnik SPARQL oparty o Oxigraph. Podczas zapytań federacyjnych iqoqo egzekwuje rygorystyczne **prawa dostępu federacyjnego**: zapytania publiczne widzą wyłącznie trójki jawnie publiczne, co gwarantuje, że prywatne zbiory nigdy nie wyciekną przez trawersowanie grafu.
`,
    },
  },
  {
    slug: "curators-handbook",
    category: "curation",
    title: {
      en: "The Curator's Handbook: Mastering Complex FRBR Cases",
      pl: "Podręcznik Kustosza: Zaawansowane przypadki modelowania FRBR",
    },
    description: {
      en: "Essential ontologist guidance for series numbering, hybrid multi-carrier box sets, expansions, and deduplication.",
      pl: "Niezbędnik ontologa: numeracja serii, wielonośnikowe zestawy hybrydowe, dodatki i deduplikacja.",
    },
    content: {
      en: `# The Curator's Handbook: Mastering Complex FRBR Cases

Welcome to the Curatorial team! While iqoqo's automated ingestion pipeline handles 90% of everyday barcode scans by querying OpenLibrary, Google Books, Discogs, MusicBrainz, BoardGameGeek (BGG), IGDB, and TMDB, the real magic of a semantic catalog lies in how we model the **non-trivial 10%**.

As a Curator (Custodian) or Admin, you have access to the Content & FRBR Editor, the Duplicate Reviewer, and the Escalation Queue. This guide focuses not on which buttons to click, but on **how to think like an ontologist** when modeling complex, real-world media.

---

## 1. Series, Franchises, and Multi-Series Memberships

In the real world, creative works rarely exist in isolation—and they almost never follow a neat, single-line numbering system.

### The Golden Rule: Series Live at the Work (F1) Level

A literary series, trilogy, or board game line is an abstract grouping of **Works**, *not* Manifestations. Why? Because *The Two Towers* is Book 2 of *The Lord of the Rings* regardless of whether it is published in English or Polish, or printed in hardcover or paperback.

### Handling Multi-Series Membership

Many Works belong to **more than one series simultaneously**, often with different volume numbers:
* **Sub-series vs. Chronological Universe:** Terry Pratchett's *Guards! Guards!* is **Book 8** in the overarching *Discworld* series, but **Book 1** in the *City Watch* sub-series.

* **Publication Order vs. Internal Chronology:** C.S. Lewis's *The Magician's Nephew* is **Book 1** chronologically in *The Chronicles of Narnia*, but **Book 6** by original publication order.

**How to curate this in iqoqo:**
1. Open the target **Work** in the FRBR Editor.
2. Open the **Relations & Series** manager.
3. Rather than cramming series names into the Work's title (never name a Work \`"Guards! Guards! (Discworld #8)"\`), add structured **Series Memberships**.
4. You can attach a single Work to **multiple Series entities**, assigning a distinct \`Series Number / Position\` (which supports decimals like \`1.5\` for novellas) to each membership.

### Omnibus Editions and Box Sets

What happens when a single physical book contains all three volumes of a trilogy (e.g., *The Lord of the Rings* single-volume omnibus)?

* **If the omnibus is a recognized canonical work of its own:** Model it as a container **Work** linked via whole/part relationships (\`hasPart\`) to the individual Works.

* **If it is purely a publisher's bundling:** Keep the omnibus as a **Manifestation** that embodies the combined Expressions of those Works, and clearly note the included volumes in the Manifestation subtitle or description.

---

## 2. Multi-Carrier & Hybrid Items (e.g., Blu-ray + CD, Book + Vinyl)

Collectors frequently encounter hybrid packages: a "Deluxe Edition" album that includes 2 Vinyl LPs, 1 CD, and a Blu-ray audio disc; or a collector's movie release that includes a 4K UHD disc, a standard Blu-ray, and a 64-page hardcover artbook.

![Multi-Carrier and Hybrid Box Set Modeling](/images/help/curator-hybrid-sets.jpg)

### How to Model Hybrid Packages

Do **not** split a single retail box set into separate Manifestations unless the components are sold separately with their own distinct retail barcodes.
1. **Single Manifestation (F3):** Create one Manifestation representing the retail package as released by the publisher/label (tied to the box's EAN/UPC barcode).
2. **Dynamic Format Normalization:** In the Manifestation editor, select the primary \`Physical Kind\` (\`audio\`, \`video\`, \`book\`, \`boardgame\`) that best represents the core nature of the release, and use the **Format** and **Extended Metadata** fields to record the hybrid carriers (e.g., \`2xLP + CD + Blu-ray\`, number of discs, or accompanying booklet details).
3. **Multi-Scan Item Gallery (F4):** At the Item or Manifestation gallery level, take advantage of iqoqo's multi-image support. You can attach separate high-resolution scans for the front box, back tracklist, Disc 1, Disc 2, and booklet so collectors can inspect every piece of the hybrid set.

---

## 3. Board Game Expansions & Container Aggregation

Board gamers face a unique physical storage problem: they buy a Base Game (*Catan*) and three expansions (*Seafarers*, *Cities & Knights*, *5-6 Player Extension*), and then **throw away the expansion boxes** to store all the wooden pieces inside the main Base Game box.

In iqoqo, we solve this by separating **conceptual dependency** from **physical storage**:

* **At the Work Level (F1 — Conceptual):** 
  * The Base Game and each Expansion are **separate Works**.

  * Link the Expansion Work to the Base Game Work using the \`isExpansionOf\` (\`requiresBaseGame\`) semantic relation in the FRBR Editor.

  * Assign standardized **BGG Mechanics** vocabulary tags at the Work level.

* **At the Item Level (F4 — Physical Container Aggregation):**

  * Each owned expansion still exists as an **Item** in the user's catalog (so iqoqo knows they own the expansion!), but its physical custody/location is aggregated into the Base Game's physical container.

  * When a user views the Base Game Item in their collection, iqoqo automatically aggregates player counts and displays the stored expansions right inside the parent box view!

---

## 4. Divergent Expressions of the Same Work

One of the most common curatorial mistakes is creating a new **Work** when you should be creating a new **Expression**—or vice versa. Use this decision matrix whenever you are unsure:

| Scenario | Same Work (F1)? | New Expression (F2)? | New Manifestation (F3)? | Why? |
| :--- | :---: | :---: | :---: | :--- |
| **A book is translated from Polish to English** | Yes | **Yes** | Yes | The underlying story is identical, but the translator created a new linguistic realization. |
| **An unabridged audiobook is recorded** | Yes | **Yes** | Yes | The narrator's performance and audio medium realize the text in a new way. |
| **A publisher releases a paperback 1 year after the hardcover (same text)** | Yes | No (Reuse!) | **Yes** | The text inside is word-for-word identical; only the physical binding and ISBN changed. |
| **A 2nd Edition of a textbook with rewritten chapters** | Yes | **Yes** | Yes | The intellectual text was revised, so it is a new Expression of the same core Work. |
| **A novel is adapted into a movie or a board game** | **No! (New Work)** | Yes | Yes | A movie or board game is an entirely new artistic creation. Link via \`isAdaptationOf\`! |

### Pro-Tip: Contributor Roles Belong to Their Tier!

When curating contributors in the FRBR Editor, always attach the person to the tier where their labor actually happened:
* **Work (F1) Contributors:** Author, Composer, Game Designer, Director, Original Artist.

* **Expression (F2) Contributors:** Translator, Narrator, Illustrator (if specific to an illustrated edition), Remastering Engineer, Conductor/Performer.

* **Manifestation (F3) Contributors:** Cover Designer, Typesetter, Publisher, Vinyl Mastering/Lacquer Cutting Engineer.

---

## 5. Deduplication, Merging, and Provider Enrichment

When users scan obscure barcodes or add items manually, duplicate Works, Expressions, or Manifestations can sneak into the graph.

![Multi-Tier Deduplication and Tombstone Redirects](/images/help/curator-deduplication.jpg)

### Resolving Duplicates Safely

Navigate to the Duplicate Reviewer to inspect system-flagged candidates across all three tiers:
1. **Select the Surviving Target:** Always choose the entity with the richest semantic links (Wikidata/VIAF URIs) and cleanest history as your primary target.
2. **Non-Destructive Consolidation:** When you merge two Manifestations, iqoqo **never orphans a user's physical Item**. All Items (F4), lending histories, wishlists, roadmaps, and social ratings attached to the duplicate are atomically re-parented to the surviving entity.
3. **Immutable Tombstones:** For federation and Semantic Web integrity, the merged-away entity's URI is converted into a **Tombstone** that permanently redirects to the surviving URI.

### Multi-Provider Metadata Gap-Filling

If a Manifestation has a valid ISBN/Barcode but is missing cover art, page counts, or descriptions, open it in the Content Editor and trigger **Provider Merge / Refetch**. iqoqo will query multiple upstream providers in parallel, allowing you to cherry-pick the best cover from one provider and the richest synopsis from another without overwriting your manual curatorial fixes.

### Linked Open Data (LOD) Reconciliation

Finally, visit the LOD Reconciliation Dashboard to link local Works and Contributors to global Semantic Web authorities (**Wikidata**, **VIAF**, **MusicBrainz**, **GeoNames**). Establishing an \`owl:sameAs\` link at the Work level allows iqoqo to automatically federated-match your catalog with other iqoqo instances around the world!
`,
      pl: `# Podręcznik Kustosza: Zaawansowane przypadki modelowania FRBR

Witaj w zespole Kustoszy! Choć automatyczny potok pobierania danych w iqoqo bez trudu radzi sobie z 90% codziennych skanów kodów kreskowych, odpytując OpenLibrary, Google Books, Discogs, MusicBrainz, BoardGameGeek (BGG), IGDB i TMDB, prawdziwa siła katalogu semantycznego tkwi w modelowaniu **nietrywialnych 10%**.

Jako Kustosz lub Administrator masz dostęp do Edytora Treści i FRBR, Modułu Deduplikacji oraz Kolejki Zgłoszeń. Ten podręcznik nie skupia się na klikaniu przycisków, lecz na **sposobie myślenia ontologa** podczas modelowania złożonych obiektów kultury.

---

## 1. Serie, uniwersa i wielokrotna przynależność do cykli

W świecie rzeczywistym dzieła rzadko istnieją w próżni — i niemal nigdy nie poddają się prostemu, jednoliniowemu numerowaniu.

### Złota zasada: Serie żyją na poziomie Dzieła (F1)

Cykl literacki, trylogia filmowa czy seria gier to abstrakcyjne grupowanie **Dzieł**, a *nie* Manifestacji. Dlaczego? Ponieważ *Dwie Wieże* są 2. tomem *Władcy Pierścieni* niezależnie od tego, czy wydano je po polsku czy po angielsku, w twardej czy w miękkiej oprawie.

### Obsługa wielokrotnej przynależności do serii

Wiele Dzieł należy do **więcej niż jednej serii jednocześnie**, często z inną numeracją:
* **Podseria a Chronologia uniwersum:** Powieść Terry'ego Pratchetta *Straż! Straż!* to **8. tom** cyklu *Świat Dysku*, ale jednocześnie **1. tom** podserii *Straż Miejska*.

* **Kolejność publikacji a Chronologia wewnętrzna:** *Siostrzeniec czarodzieja* C.S. Lewisa to tom 1. pod względem chronologii wydarzeń w *Opowieściach z Narnii*, ale tom 6. według kolejności powstawania.

**Jak zamodelować to w iqoqo:**
1. Otwórz docelowe **Dzieło** w Edytorze FRBR.
2. Przejdź do zakładki **Relacje i Serie**.
3. Zamiast wpisywać nazwę serii w tytule Dzieła (nigdy nie nazywaj dzieła \`"Straż! Straż! (Świat Dysku #8)"\`), dodaj ustrukturyzowaną **Przynależność do Serii**.
4. Możesz przypisać jedno Dzieło do **wielu obiektów Serii**, określając osobną pozycję/numer (z obsługą wartości dziesiętnych, np. \`1.5\` dla nowel).

### Wydania zbiorcze (Omnibus) i pakiety

Co zrobić, gdy pojedyncza fizyczna książka zawiera wszystkie trzy tomy trylogii?

* **Jeśli omnibus jest powszechnie uznanym, odrębnym bytem:** Utwórz dla niego kontenerowe **Dzieło** połączone relacjami części (\`hasPart\`) z poszczególnymi Dziełami składowymi.

* **Jeśli to wyłącznie zabieg wydawcy pakującego kilka tomów pod jeden ISBN:** Pozostaw omnibus jako **Manifestację**, która ucieleśnia połączone Ekspresje tych tomów, podając zawarte części w podtytule lub opisie.

---

## 2. Zestawy hybrydowe i wielonośnikowe (np. Blu-ray + CD, Książka + Winyl)

Kolekcjonerzy często spotykają wydania hybrydowe: album „Deluxe Edition” zawierający 2 płyty winylowe, 1 płytę CD i krążek Blu-ray audio; albo kolekcjonerskie wydanie filmu z płytą 4K UHD, zwykłym Blu-ray i 64-stronicowym artbookiem w twardej oprawie.

![Modelowanie wydań hybrydowych i wielonośnikowych box setów](/images/help/curator-hybrid-sets.jpg)

### Jak modelować wydania hybrydowe

**Nie rozbijaj** pojedynczego zestawu sklepowego na osobne Manifestacje, chyba że jego elementy były sprzedawane osobno z własnymi kodami kreskowymi.
1. **Pojedyncza Manifestacja (F3):** Utwórz jedną Manifestację reprezentującą całe pudełko wydane przez wytwórnię (powiązaną z kodem kreskowym zestawu).
2. **Normalizacja formatów:** W edytorze wybierz wiodący rodzaj nośnika (\`audio\`, \`wideo\`, \`książka\`, \`planszówka\`), a w polach formatu i metadanych rozszerzonych opisz nośniki składowe (np. \`2xLP + CD + Blu-ray\`, liczba płyt, dołączona książeczka).
3. **Wielozdjęciowa galeria egzemplarza (F4):** Skorzystaj z galerii wielozdjęciowej w iqoqo. Możesz dołączyć osobne skany dla frontu pudełka, spisu utworów, płyty 1, płyty 2 i książeczki.

---

## 3. Dodatki do gier planszowych i agregacja pudełek

Fani gier planszowych stają przed dylematem: kupują grę podstawową (*Catan*) oraz trzy rozszerzenia (*Żeglarze*, *Miasta i Rycerze*, *Rozszerzenie dla 5-6 graczy*), po czym **wyrzucają pudełka z dodatków**, aby zmieścić wszystkie drewniane elementy w głównym pudełku gry podstawowej.

W iqoqo rozwiązujemy to poprzez rozdzielenie **zależności koncepcyjnej** od **fizycznego przechowywania**:

* **Na poziomie Dzieła (F1 — koncepcja):**

  * Gra podstawowa oraz każdy dodatek to **osobne Dzieła**.

  * Połącz Dzieło dodatku z Dziełem gry podstawowej za pomocą relacji \`isExpansionOf\` (\`requiresBaseGame\`) w Edytorze FRBR.

  * Przypisz ustandaryzowane tagi mechanik z serwisu BGG na poziomie Dzieła.

* **Na poziomie Egzemplarza (F4 — fizyczny kontener):**

  * Każdy posiadany dodatek nadal istnieje jako **Egzemplarz** w katalogu użytkownika, lecz jego lokalizacja fizyczna jest zagregowana w pojemniku gry podstawowej.

  * Gdy użytkownik przegląda grę podstawową, iqoqo automatycznie sumuje liczbę graczy i wyświetla przechowywane dodatki wewnątrz karty głównego pudełka!

---

## 4. Różne Ekspresje tego samego Dzieła

Jednym z najczęstszych błędów kustoszy jest tworzenie nowego **Dzieła** tam, gdzie powinna powstać nowa **Ekspresja** — lub odwrotnie. Poniższa matryca decyzji pomoże Ci w wątpliwych sytuacjach:

| Sytuacja | To samo Dzieło (F1)? | Nowa Ekspresja (F2)? | Nowa Manifestacja (F3)? | Dlaczego? |
| :--- | :---: | :---: | :---: | :--- |
| **Książka przetłumaczona z angielskiego na polski** | Tak | **Tak** | Tak | Ta sama fabuła, lecz tłumacz stworzył nową realizację językową. |
| **Nagranie pełnego audiobooka z lektorem** | Tak | **Tak** | Tak | Interpretacja lektora i medium audio realizują tekst w nowy sposób. |
| **Wydanie kieszonkowe rok po twardej oprawie (ten sam tekst)** | Tak | Nie (Użyj istniejącej!) | **Tak** | Tekst jest identyczny; zmieniła się tylko fizyczna oprawa i numer ISBN. |
| **2. wydanie podręcznika akademickiego z nowymi rozdziałami** | Tak | **Tak** | Tak | Treść intelektualna została zmieniona — to nowa Ekspresja tego samego Dzieła. |
| **Powieść zaadaptowana na film lub grę planszową** | **Nie! (Nowe Dzieło)** | Tak | Tak | Film to całkowicie nowa kreacja artystyczna. Połącz relacją \`isAdaptationOf\`! |

### Wskazówka: Role twórców należą do właściwego poziomu!

W Edytorze FRBR zawsze przypisuj twórcę do poziomu, na którym faktycznie powstała jego praca:
* **Twórcy Dzieła (F1):** Pisarz, Kompozytor, Projektant gry, Reżyser, Pierwotny autor.

* **Twórcy Ekspresji (F2):** Tłumacz, Lektor, Ilustrator (dla wydania ilustrowanego), Inżynier masteringu, Dyrygent/Wykonawca.

* **Twórcy Manifestacji (F3):** Projektant okładki, Składacz tekstu, Wydawnictwo, Tłocznia płyt.

---

## 5. Deduplikacja, scalanie i wzbogacanie metadanych

Gdy użytkownicy skanują nietypowe kody lub dodają pozycje ręcznie, w grafie mogą pojawić się zduplikowane rekordy.

![Wielopoziomowe scalanie duplikatów i przekierowania Tombstone](/images/help/curator-deduplication.jpg)

### Bezpieczne scalanie rekordów

Przejdź do Modułu Deduplikacji, aby przejrzeć kandydatów na wszystkich trzech poziomach:
1. **Wybierz encję przetrwałą:** Zawsze wybieraj jako cel encję z najbogatszymi linkami semantycznymi (Wikidane, VIAF) i najczystszą historią.
2. **Niedestrukcyjna konsolidacja:** Gdy scalasz dwie Manifestacje, iqoqo **nigdy nie usuwa fizycznych Egzemplarzy użytkowników**. Wszystkie Egzemplarze (F4), historie wypożyczeń, listy życzeń i plany są atomowo przepinane do encji przetrwałej.
3. **Niezmienne nagrobki (Tombstones):** Dla zachowania spójności w sieci federacyjnej identyfikator scalonej encji staje się nagrobkiem (\`Tombstone\`), który trwale przekierowuje do encji przetrwałej.

### Uzupełnianie braków z wielu źródeł

Jeśli Manifestacja posiada poprawny kod kreskowy, ale brakuje jej okładki lub opisu, otwórz ją w Edytorze Treści i uruchom funkcję **Wzbogać od dostawców**. iqoqo odpyta równolegle wiele serwisów, pozwalając Ci wybrać najlepszą okładkę z jednego źródła i bogaty opis z drugiego.

### Uzgadnianie z Otwartymi Danymi Powiązanymi (LOD)

Wreszcie odwiedź Panel Uzgadniania LOD, aby powiązać lokalne Dzieła i Twórców z globalnymi autorytetami Semantic Web (**Wikidane**, **VIAF**, **MusicBrainz**, **GeoNames**). Relacja \`owl:sameAs\` pozwala iqoqo na automatyczne dopasowywanie zbiorów z innymi bibliotekami na całym świecie!
`,
    },
  },
];
