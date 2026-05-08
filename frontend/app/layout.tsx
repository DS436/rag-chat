import "./globals.css";

export const metadata = {
  title: "RAG Knowledge Base",
  description: "Upload documents and chat with grounded answers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
