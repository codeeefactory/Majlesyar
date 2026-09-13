import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CartProvider } from "@/contexts/CartContext";
import { SettingsProvider } from "@/contexts/SettingsContext";
import { AdminAuthProvider } from "@/contexts/AdminAuthContext";
import { CustomerAuthProvider } from "@/contexts/CustomerAuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { SiteThemeSync } from "@/components/SiteThemeSync";
import { RouteChangeLoader } from "@/components/RouteChangeLoader";
import HomePage from "./pages/HomePage";

const ProductPage = lazy(() => import("./pages/ProductPage"));

// Lazy loaded pages - secondary routes
const EventPage = lazy(() => import("./pages/EventPage"));
const BuilderPage = lazy(() => import("./pages/BuilderPage"));
const CartPage = lazy(() => import("./pages/CartPage"));
const CheckoutPage = lazy(() => import("./pages/CheckoutPage"));
const OrderPage = lazy(() => import("./pages/OrderPage"));
const TrackOrderPage = lazy(() => import("./pages/TrackOrderPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const BlogPage = lazy(() => import("./pages/BlogPage"));
const BlogPostPage = lazy(() => import("./pages/BlogPostPage"));
const TermsPage = lazy(() => import("./pages/TermsPage"));
const CustomerAuthPage = lazy(() => import("./pages/CustomerAuthPage"));
const CustomerDashboardPage = lazy(() => import("./pages/CustomerDashboardPage"));
const AdminLoginPage = lazy(() => import("./pages/admin/AdminLoginPage"));
const AdminOrdersPage = lazy(() => import("./pages/admin/AdminOrdersPage"));
const AdminPageProductsPage = lazy(() => import("./pages/admin/AdminPageProductsPage"));
const LazyToaster = lazy(() => import("@/components/ui/sonner").then((m) => ({ default: m.Toaster })));
const LazyFloatingContactButton = lazy(() =>
  import("./components/FloatingContactButton").then((m) => ({ default: m.FloatingContactButton })),
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
  return (
    <SettingsProvider>
      <ThemeProvider>
        <SiteThemeSync />
        <CartProvider>
          <CustomerAuthProvider>
          <DeferredToaster />
          <BrowserRouter>
            <RouteChangeLoader />
            <div id="app-routes">
              <Suspense fallback={null}>
                <Routes>
                {/* Critical SEO Route */}
                <Route path="/" element={<HomePage />} />

              {/* Lazy loaded Routes */}
              <Route path="/events/:slug" element={<EventPage />} />
              <Route path="/pack" element={<EventPage />} />
              <Route path="/pack/memorial" element={<EventPage />} />
              <Route path="/pack/personal" element={<EventPage />} />
              <Route path="/pack/memorial/luxury" element={<EventPage />} />
              <Route path="/flower" element={<EventPage />} />
              <Route path="/flower/memorial-wreaths" element={<EventPage />} />
              <Route path="/flower/bouquets" element={<EventPage />} />
              <Route path="/flower/congratulation-wreaths" element={<EventPage />} />
              <Route path="/flower/congratulatory-wreaths" element={<EventPage />} />
              <Route path="/flower/funeral-bouquet" element={<EventPage />} />
              <Route path="/flower/box" element={<EventPage />} />
              <Route path="/halva-khorma" element={<EventPage />} />
              <Route path="/halva-khorma/luxury" element={<EventPage />} />
              <Route path="/food" element={<EventPage />} />
              <Route path="/food/finger_food" element={<EventPage />} />
              <Route path="/food/charcuterie-board" element={<EventPage />} />
              <Route path="/food/shaleh-zard" element={<EventPage />} />
              <Route path="/food/ashe-rashteh" element={<EventPage />} />
              <Route path="/food/dessert" element={<EventPage />} />
              <Route path="/food/juice" element={<EventPage />} />
              <Route path="/builder" element={<BuilderPage />} />
              <Route path="/cart" element={<CartPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/order/:id" element={<OrderPage />} />
              <Route path="/track" element={<TrackOrderPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/blog" element={<BlogPage />} />
              <Route path="/blog/:slug" element={<BlogPostPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/login" element={<CustomerAuthPage />} />
              <Route path="/signup" element={<CustomerAuthPage />} />
              <Route path="/dashboard" element={<CustomerDashboardPage />} />
              <Route path="/profile" element={<CustomerDashboardPage />} />

              {/* Admin Routes - wrapped with AdminAuthProvider */}
              <Route path="/admin/login" element={<AdminRoute><AdminLoginPage /></AdminRoute>} />
              <Route path="/admin/orders" element={<AdminRoute><AdminOrdersPage /></AdminRoute>} />
              <Route path="/admin/orders/:id" element={<AdminRoute><AdminOrdersPage /></AdminRoute>} />
              <Route path="/admin/page-products" element={<AdminRoute><AdminPageProductsPage /></AdminRoute>} />

                {/* Catch-all */}
                <Route path="*" element={<ProductPage />} />
                </Routes>
              </Suspense>
            </div>
            <DeferredFloatingContactButton />
          </BrowserRouter>
          </CustomerAuthProvider>
        </CartProvider>
      </ThemeProvider>
    </SettingsProvider>
  );
};

export default App;
