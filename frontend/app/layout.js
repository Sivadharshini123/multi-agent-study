import Shell from "../components/Shell";
import "./globals.css";

export const metadata = {
  title: "Study planner",
  description: "Daily plans, tutoring, quizzes, and critiques from your own material.",
  manifest: "/manifest.json",
  applicationName: "Study planner",
  appleWebApp: { capable: true, title: "Study planner", statusBarStyle: "default" },
  icons: { icon: "/icon.svg" },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1c1915",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
