import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LocalMind",
  description: "Local Agentic RAG Assistant with Web Search and Streaming Chat"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
