"use client";

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <div className="relative w-full h-[420px] flex items-center justify-center overflow-hidden rounded-xl mb-12">
      <div className="absolute inset-0 z-0">
        <Image
          src="/inside-library-photo.svg"
          alt="Inside the library"
          fill
          className="object-cover opacity-40"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
      </div>

      <div className="relative z-10 text-center px-4 max-w-3xl">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
          The Library of Everything
        </h1>
        <p className="text-xl text-muted-foreground mb-8">
          iqoqo empowers you to create, share, and discover personal catalogs
          of books, music, movies, and board games. Built on the open Semantic
          Web, designed for a distributed future.
        </p>
        <div className="flex gap-4 justify-center">
          <Button asChild size="lg">
            <Link href="/register">Start Your Catalog</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/collection">Browse Instance</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
