import { Footer } from './Footer';
import { Header } from './Header';

interface AppShellProps {
  children: React.ReactNode;
  hideFooter?: boolean;
}

export function AppShell({ children, hideFooter = false }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <main className="flex-1">
        {children}
      </main>
      {!hideFooter && <Footer />}
    </div>
  );
}
