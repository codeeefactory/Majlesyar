import { lazy, Suspense } from 'react';
import { Header } from './Header';

const LazyFooter = lazy(() => import('./Footer').then((m) => ({ default: m.Footer })));

interface AppShellProps {
  children: React.ReactNode;
  hideFooter?: boolean;
}

export function AppShell({ children, hideFooter = false }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <main id="main-content" className="flex-1">
        {children}
      </main>
      {!hideFooter && (
        <Suspense
          fallback={
            <footer className="bg-card border-t border-border mt-auto" aria-hidden="true">
              <div className="container py-12" />
            </footer>
          }
        >
          <LazyFooter />
        </Suspense>
      )}
    </div>
  );
}
