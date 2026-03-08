import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  ],
  pages: {
    signIn: "/login", // Tells NextAuth to use your custom login page
  },
  callbacks: {
    // This runs whenever a session is checked
    async session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
    // This runs when a user logs in
    async jwt({ token, user, account }) {
      if (account && user) {
        // TODO: In the future, you can send the Google token to your Python backend here
        // to sync the user into your SQLAlchemy database!
        token.id = user.id;
      }
      return token;
    },
  },
  session: { strategy: "jwt" },
});
