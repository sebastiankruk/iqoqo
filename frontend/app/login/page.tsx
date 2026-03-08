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

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.ok) {
      const data = await res.json();
      // Exchange token in BFF
      window.location.href = `/api/auth/exchange?token=${data.token}`;
    } else {
      alert("Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Sign in to iqoqo</h1>
        <Button
            className="w-full"
            variant="outline"
            onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/login/google`}>
          Sign in with Google
        </Button>
        <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:block after:border-b after:border-border">
          <span className="relative z-10 bg-background px-2 text-muted-foreground">Or</span>
        </div>
        <form onSubmit={handleLocalLogin} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            className="w-full rounded border px-3 py-2 text-sm text-black"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full rounded border px-3 py-2 text-sm text-black"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" className="w-full">Sign In</Button>
        </form>
      </div>
    </div>
  );
}
