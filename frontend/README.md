# iqoqo Frontend

Modern React/Next.js frontend for the iqoqo Library of Everything application.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4.x
- **UI Components**: shadcn/ui (planned)
- **State Management**: TanStack Query + Zustand (planned)
- **Forms**: React Hook Form + Zod (planned)

## Getting Started

### Prerequisites

- Node.js 20 or later
- npm or pnpm
- Backend API running on port 5000

### Development Setup

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Configure environment variables:**

   Copy `.env.example` to `.env.local` and update values:

   ```bash
   cp .env.example .env.local
   ```

   For local development, ensure:

   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:5000
   ```

3. **Run the development server:**

   ```bash
   npm run dev
   ```

   The frontend will be available at [http://localhost:3000](http://localhost:3000)

### Docker Development

To run with Docker Compose (includes backend and database):

```bash
# From project root
docker-compose up frontend
```

## Project Structure

```text
frontend/
├── app/                    # Next.js App Router pages
├── components/             # React components (to be added)
│   ├── layout/            # Layout components
│   ├── dashboard/         # Dashboard components
│   ├── scanner/           # Scanner components
│   └── item/              # Item components
├── lib/                   # Utilities and helpers
├── hooks/                 # Custom React hooks
├── types/                 # TypeScript type definitions
├── public/                # Static assets
└── styles/                # Global styles
```

## API Integration

The frontend communicates with the Flask backend API. Key endpoints:

- `GET /api/health` - Health check
- `GET /api/stats` - Dashboard statistics
- `GET /api/items` - List items (with pagination)
- `GET /api/items/:id` - Get item details
- `PUT /api/items/:id` - Update item
- `DELETE /api/items/:id` - Delete item
- `GET /api/isbn/:isbn` - ISBN lookup
- `POST /api/isbn/:isbn` - Update manifestation

## Design System

**Modern Athenaeum Theme:**

- **Primary Color**: Deep Indigo (#2C3E50)
- **Background**: Warm Paper (#FDFBF7)
- **Accent**: Library Clay (#D35400)
- **Typography**:
  - Headings: Merriweather (serif)
  - UI: Inter (sans-serif)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial

## Contributing

This is part of the iqoqo project migration from Flask/jQuery to React/Next.js. See the main project documentation for contribution guidelines.

## License

See LICENSE file in project root.
