import "./globals.css";

export const metadata = {
  title: "Urban Canopy Pipeline",
  description: "Cross-city urban cooling analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
