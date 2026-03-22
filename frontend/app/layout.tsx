import "./globals.css";

import FrontendLogger from "../components/FrontendLogger";

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
      <body>
        <FrontendLogger />
        {children}
      </body>
    </html>
  );
}
