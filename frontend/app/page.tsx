import { Navbar } from "@/components/dashboard/navbar";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { CurrentContext } from "@/components/dashboard/current-context";
import { FreshArrivals } from "@/components/dashboard/fresh-arrivals";

export default function DashboardPage() {
  const uiVersion = process.env.NEXT_PUBLIC_APP_VERSION || 'dev';

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <h1 className="font-serif text-2xl font-bold text-foreground">
            Welcome to your library
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your collection is growing nicely. Here is what is happening.
          </p>
        </div>

        <div className="flex flex-col gap-10">
          <StatsCards />
          <CurrentContext />
          <FreshArrivals />
        </div>
      </main>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <p className="text-xs text-muted-foreground">
            <span className="font-serif font-bold text-foreground">iqoqo</span>
            {" "}&middot;{" "}The Library of Everything
            {" "}&middot;{" "}{uiVersion}
          </p>
          <p className="text-xs text-muted-foreground">Your library, your rules.</p>
        </div>
      </footer>
    </div>
  );
}
