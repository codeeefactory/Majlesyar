import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CartProvider } from "@/contexts/CartContext";
import { SettingsProvider } from "@/contexts/SettingsContext";
import { AdminAuthProvider } from "@/contexts/AdminAuthContext";
import { SiteThemeSync } from "@/components/SiteThemeSync";
import { measureAndStoreClientPing } from "@/lib/network";
import ProductPage from "./pages/ProductPage";

// Keep product route eager; defer homepage code on non-home routes.
const HomePage = lazy(() => import("./pages/HomePage"));

// Lazy loaded pages - secondary routes
const ShopPage = lazy(() => import("./pages/ShopPage"));
const EventPage = lazy(() => import("./pages/EventPage"));
const BuilderPage = lazy(() => import("./pages/BuilderPage"));
const CartPage = lazy(() => import("./pages/CartPage"));
const CheckoutPage = lazy(() => import("./pages/CheckoutPage"));
const OrderPage = lazy(() => import("./pages/OrderPage"));
const TrackOrderPage = lazy(() => import("./pages/TrackOrderPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const AdminLoginPage = lazy(() => import("./pages/admin/AdminLoginPage"));
const AdminOrdersPage = lazy(() => import("./pages/admin/AdminOrdersPage"));
const NotFound = lazy(() => import("./pages/NotFound"));
const LazyToaster = lazy(() => import("@/components/ui/sonner").then((m) => ({ default: m.Toaster })));
const LazyFloatingContactButton = lazy(() =>
  import("./components/FloatingContactButton").then((m) => ({ default: m.FloatingContactButton })),
);

// Loading fallback
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
  </div>
);

// Admin route wrapper - only loads AdminAuthProvider for admin pages
function AdminRoute({ children }: { children: React.ReactNode }) {
  return <AdminAuthProvider>{children}</AdminAuthProvider>;
}

function DeferredToaster() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      setIsVisible(true);
    }, 800);
    return () => window.clearTimeout(timerId);
  }, []);

  if (!isVisible) return null;

  return (
    <Suspense fallback={null}>
      <LazyToaster position="top-center" />
    </Suspense>
  );
}

function DeferredFloatingContactButton() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      setIsVisible(true);
    }, 1200);
    return () => window.clearTimeout(timerId);
  }, []);

  if (!isVisible) return null;

  return (
    <Suspense fallback={null}>
      <LazyFloatingContactButton />
    </Suspense>
  );
}

const App = () => {
  useEffect(() => {
    void measureAndStoreClientPing();
  }, []);

  return (
    <SettingsProvider>
      <SiteThemeSync />
      <CartProvider>
        <DeferredToaster />
        <BrowserRouter>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Critical SEO Route */}
              <Route path="/" element={<HomePage />} />

              {/* Lazy loaded Routes */}
              <Route path="/shop" element={<ShopPage />} />
              <Route path="/product/:slug" element={<ProductPage />} />
              <Route path="/events/:slug" element={<EventPage />} />
              <Route path="/builder" element={<BuilderPage />} />
              <Route path="/cart" element={<CartPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/order/:id" element={<OrderPage />} />
              <Route path="/track" element={<TrackOrderPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/about" element={<AboutPage />} />

              {/* Admin Routes - wrapped with AdminAuthProvider */}
              <Route path="/admin/login" element={<AdminRoute><AdminLoginPage /></AdminRoute>} />
              <Route path="/admin/orders" element={<AdminRoute><AdminOrdersPage /></AdminRoute>} />
              <Route path="/admin/orders/:id" element={<AdminRoute><AdminOrdersPage /></AdminRoute>} />

              {/* Catch-all */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          <DeferredFloatingContactButton />
        </BrowserRouter>
      </CartProvider>
    </SettingsProvider>
  );
};

export default App;
