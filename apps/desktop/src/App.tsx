import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { LocaleProvider } from "@/context/LocaleContext";
import { MarketplaceModeProvider } from "@/context/MarketplaceModeContext";
import { AppShell } from "@/components/layout/AppShell";
import { AuthLayout } from "@/pages/auth/AuthLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { ExplorePage } from "@/pages/ExplorePage";
import { ActivityPage } from "@/pages/ActivityPage";
import { ListingsPage } from "@/pages/ListingsPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { OpenRequestsPage } from "@/pages/assistance/OpenRequestsPage";
import { ProviderPortfolioPage } from "@/pages/assistance/ProviderPortfolioPage";
import { RequestOffersPage } from "@/pages/assistance/RequestOffersPage";
import { ServiceRequestPage } from "@/pages/assistance/ServiceRequestPage";
import { RentalDetailPage } from "@/pages/RentalDetailPage";
import { MessagesPage } from "@/pages/MessagesPage";
import { ConversationPage } from "@/pages/ConversationPage";
import { AdminPage } from "@/pages/AdminPage";
import { NotificationsPage } from "@/pages/NotificationsPage";
import { SavedPage } from "@/pages/SavedPage";
import { CommunityPage } from "@/pages/CommunityPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { DisputesPage } from "@/pages/DisputesPage";
import { MentorshipPage } from "@/pages/MentorshipPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { AdminRoute } from "@/routes/AdminRoute";
import { useAuth } from "@/context/AuthContext";

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/app/explore" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <LocaleProvider>
        <MarketplaceModeProvider>
          <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/app/explore" replace />} />
            <Route element={<AuthLayout />}>
              <Route
                path="/login"
                element={
                  <GuestOnly>
                    <LoginPage />
                  </GuestOnly>
                }
              />
              <Route
                path="/register"
                element={
                  <GuestOnly>
                    <RegisterPage />
                  </GuestOnly>
                }
              />
            </Route>
            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="explore" replace />} />
              <Route path="explore" element={<ExplorePage />} />
              <Route path="rentals/:listingId" element={<RentalDetailPage />} />
              <Route path="assistance/request" element={<ServiceRequestPage />} />
              <Route path="assistance/portfolio" element={<ProviderPortfolioPage />} />
              <Route path="assistance/open-jobs" element={<OpenRequestsPage />} />
              <Route path="assistance/requests/:requestId/offers" element={<RequestOffersPage />} />
              <Route path="activity" element={<ActivityPage />} />
              <Route path="messages" element={<MessagesPage />} />
              <Route path="messages/:conversationId" element={<ConversationPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="listings" element={<ListingsPage />} />
              <Route path="saved" element={<SavedPage />} />
              <Route path="community" element={<CommunityPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="disputes" element={<DisputesPage />} />
              <Route path="mentorship" element={<MentorshipPage />} />
              <Route
                path="admin"
                element={
                  <AdminRoute>
                    <AdminPage />
                  </AdminRoute>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/app/explore" replace />} />
          </Routes>
          </BrowserRouter>
        </MarketplaceModeProvider>
      </LocaleProvider>
    </AuthProvider>
  );
}
