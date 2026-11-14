const STORAGE_ACCESS = "nl_access_token";
const STORAGE_REFRESH = "nl_refresh_token";

function apiBase(): string {
  return window.neighbourlink?.apiBaseUrl ?? "http://127.0.0.1:8742/api/v1";
}

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type Profile = {
  display_name: string;
  bio: string | null;
  phone: string | null;
  preferred_locale: string;
  approximate_location: string | null;
};

export type Me = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  profile: Profile;
  roles: { slug: string; name: string }[];
};

export function getAccessToken(): string | null {
  return localStorage.getItem(STORAGE_ACCESS);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(STORAGE_REFRESH);
}

export function setTokens(tokens: TokenResponse): void {
  localStorage.setItem(STORAGE_ACCESS, tokens.access_token);
  localStorage.setItem(STORAGE_REFRESH, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(STORAGE_ACCESS);
  localStorage.removeItem(STORAGE_REFRESH);
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const res = await fetch(`${apiBase()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return false;
  }
  const data = (await res.json()) as TokenResponse;
  setTokens(data);
  return true;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      "Cannot reach the NeighbourLink API. Start Docker, then run the backend on http://127.0.0.1:8742 (see README)."
    );
  }

  if (res.status === 401 && retry) {
    const refreshed = await tryRefresh();
    if (refreshed) return apiFetch<T>(path, options, false);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = (await res.json()) as { detail?: string };
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function register(email: string, password: string, displayName: string) {
  const data = await apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  setTokens(data);
  return data;
}

export async function login(email: string, password: string) {
  const data = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setTokens(data);
  return data;
}

export async function logout() {
  try {
    await apiFetch<void>("/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}

export async function fetchMe() {
  return apiFetch<Me>("/me");
}

export async function updateProfile(patch: Partial<Profile>) {
  return apiFetch<Profile>("/me/profile", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export type RentalCategory = { slug: string; name: string };

export function apiOrigin(): string {
  const base = window.neighbourlink?.apiBaseUrl ?? "http://127.0.0.1:8742/api/v1";
  return base.replace(/\/api\/v1\/?$/, "");
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${apiBase()}${path}`, { method: "POST", headers, body: formData });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = (await res.json()) as { detail?: string };
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export type ListingPublic = {
  id: string;
  title: string;
  description: string;
  condition: string;
  daily_price_cents: number;
  deposit_cents: number;
  status: string;
  public_area_label: string;
  category: RentalCategory;
  owner_display_name: string;
  latitude: number;
  longitude: number;
  distance_meters?: number | null;
  created_at: string;
  photo_urls?: string[];
};

export type ListingOwner = ListingPublic & {
  exact_address: string | null;
  pickup_instructions: string | null;
};

export type ListingSearchParams = {
  q?: string;
  category?: string;
  min_price_cents?: number;
  max_price_cents?: number;
  latitude?: number;
  longitude?: number;
  radius_km?: number;
  sort?: "relevance" | "price_asc" | "price_desc" | "distance";
};

export async function fetchRentalCategories() {
  return apiFetch<RentalCategory[]>("/rental-categories");
}

export async function searchListings(params: ListingSearchParams = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  const query = qs.toString();
  return apiFetch<ListingPublic[]>(`/listings${query ? `?${query}` : ""}`);
}

export async function fetchMyListings() {
  return apiFetch<ListingOwner[]>("/me/listings");
}

export type ListingCreateBody = {
  category_slug: string;
  title: string;
  description: string;
  condition: "new" | "like_new" | "good" | "fair";
  daily_price_cents: number;
  deposit_cents?: number;
  public_area_label: string;
  exact_address?: string | null;
  latitude: number;
  longitude: number;
  pickup_instructions?: string | null;
};

export async function createListing(body: ListingCreateBody) {
  return apiFetch<ListingOwner>("/listings", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchListing(id: string) {
  return apiFetch<ListingPublic>(`/listings/${id}`);
}

export type ItemAvailability = {
  item_id: string;
  blocks: { id: string; start_date: string; end_date: string; note: string | null }[];
  busy: { start_date: string; end_date: string; kind: string }[];
};

export async function fetchListingAvailability(itemId: string) {
  return apiFetch<ItemAvailability>(`/listings/${itemId}/availability`);
}

export async function addAvailabilityBlock(
  itemId: string,
  body: { start_date: string; end_date: string; note?: string | null }
) {
  return apiFetch<ItemAvailability["blocks"][0]>(`/listings/${itemId}/availability/blocks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteAvailabilityBlock(itemId: string, blockId: string) {
  return apiFetch<void>(`/listings/${itemId}/availability/blocks/${blockId}`, { method: "DELETE" });
}

export type BookingQuote = {
  start_date: string;
  end_date: string;
  rental_days: number;
  daily_price_cents: number;
  deposit_cents: number;
  subtotal_cents: number;
  total_cents: number;
};

export async function fetchBookingQuote(itemId: string, startDate: string, endDate: string) {
  const qs = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiFetch<BookingQuote>(`/listings/${itemId}/booking-quote?${qs}`);
}

export type RentalBooking = {
  id: string;
  item_id: string;
  item_title: string;
  status: string;
  start_date: string;
  end_date: string;
  rental_days: number;
  subtotal_cents: number;
  total_cents: number;
  deposit_cents_snapshot: number;
  daily_price_cents_snapshot: number;
  renter_note: string | null;
  owner_note: string | null;
  created_at: string;
  is_owner_view: boolean;
  renter_display_name: string | null;
  hold_expires_at?: string | null;
  paid_at?: string | null;
  pickup_at?: string | null;
  return_at?: string | null;
  deposit_escrow_status?: string | null;
  completed_at?: string | null;
};

export type PaymentIntent = {
  payment_id: string;
  rental_booking_id: string;
  amount_cents: number;
  currency: string;
  status: string;
  provider: string;
  idempotency_key: string;
  checkout_token: string;
};

export async function requestBooking(itemId: string, body: { start_date: string; end_date: string; renter_note?: string }) {
  return apiFetch<RentalBooking>(`/listings/${itemId}/booking-requests`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMyRentalBookings() {
  return apiFetch<RentalBooking[]>("/me/rental-bookings");
}

export async function fetchOwnerBookingRequests() {
  return apiFetch<RentalBooking[]>("/me/owner/booking-requests");
}

export async function acceptBooking(bookingId: string, ownerNote?: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/accept`, {
    method: "POST",
    body: JSON.stringify({ owner_note: ownerNote ?? null }),
  });
}

export async function declineBooking(bookingId: string, ownerNote?: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/decline`, {
    method: "POST",
    body: JSON.stringify({ owner_note: ownerNote ?? null }),
  });
}

export async function cancelBooking(bookingId: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/cancel`, { method: "POST" });
}

export async function createPaymentIntent(bookingId: string) {
  return apiFetch<PaymentIntent>(`/rental-bookings/${bookingId}/payment-intent`, { method: "POST" });
}

export async function sandboxPayBooking(bookingId: string, paymentId: string) {
  return apiFetch<{ status: string }>(
    `/rental-bookings/${bookingId}/sandbox-pay?payment_id=${encodeURIComponent(paymentId)}`,
    { method: "POST" }
  );
}

export async function recordPickup(bookingId: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/pickup`, { method: "POST" });
}

export async function recordReturn(bookingId: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/return`, { method: "POST" });
}

export async function confirmRentalComplete(bookingId: string) {
  return apiFetch<RentalBooking>(`/rental-bookings/${bookingId}/complete`, { method: "POST" });
}

export type ConditionReport = {
  id: string;
  phase: string;
  notes: string | null;
  damage_notes: string | null;
  photos: { id: string; url: string; original_filename: string }[];
  owner_acknowledged_at: string | null;
  renter_acknowledged_at: string | null;
};

export async function fetchConditionReports(bookingId: string) {
  return apiFetch<ConditionReport[]>(`/rental-bookings/${bookingId}/condition-reports`);
}

export async function submitConditionReport(
  bookingId: string,
  phase: "pickup" | "return",
  files: File[],
  notes: string,
  damageNotes: string
) {
  const form = new FormData();
  form.append("phase", phase);
  if (notes) form.append("notes", notes);
  if (damageNotes) form.append("damage_notes", damageNotes);
  files.forEach((f) => form.append("photos", f));
  return apiUpload<ConditionReport>(`/rental-bookings/${bookingId}/condition-reports`, form);
}

export async function acknowledgeConditionReport(bookingId: string, reportId: string) {
  return apiFetch<ConditionReport>(`/rental-bookings/${bookingId}/condition-reports/${reportId}/acknowledge`, {
    method: "POST",
  });
}

export async function uploadListingPhoto(listingId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<{ url: string }>(`/listings/${listingId}/photos`, form);
}

export type ServiceCategory = { slug: string; name: string; requires_verification?: boolean };

export type ProviderPublic = {
  user_id: string;
  display_name: string;
  headline: string;
  introduction: string;
  service_area_label: string;
  latitude: number;
  longitude: number;
  categories: ServiceCategory[];
  assistance_rating: number | null;
  assistance_rating_count: number;
  distance_meters?: number | null;
};

export async function fetchServiceCategories() {
  return apiFetch<ServiceCategory[]>("/service-categories");
}

export async function searchProviders(params: {
  category?: string;
  latitude?: number;
  longitude?: number;
  radius_km?: number;
}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  const q = qs.toString();
  return apiFetch<ProviderPublic[]>(`/providers${q ? `?${q}` : ""}`);
}

export async function upsertProviderPortfolio(body: {
  headline: string;
  introduction: string;
  service_area_label: string;
  latitude: number;
  longitude: number;
  category_slugs: string[];
}) {
  return apiFetch<ProviderPublic>("/me/provider-portfolio", { method: "PUT", body: JSON.stringify(body) });
}

export type ServiceRequest = {
  id: string;
  title: string;
  description: string;
  status: string;
  service_area_label: string;
  budget_cents: number | null;
  category: ServiceCategory;
  offer_count: number;
  created_at: string;
};

export async function createServiceRequest(body: {
  category_slug: string;
  title: string;
  description: string;
  service_area_label: string;
  latitude: number;
  longitude: number;
  budget_cents?: number;
}) {
  return apiFetch<ServiceRequest>("/service-requests", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMyServiceRequests() {
  return apiFetch<ServiceRequest[]>("/me/service-requests");
}

export async function fetchOpenServiceRequests(category?: string) {
  const q = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch<ServiceRequest[]>(`/service-requests/open${q}`);
}

export type ServiceOffer = {
  id: string;
  provider_id: string;
  provider_name: string;
  price_cents: number;
  included_work: string;
  excluded_work: string | null;
  estimated_days: number;
  status: string;
  created_at: string;
};

export async function fetchRequestOffers(requestId: string) {
  return apiFetch<ServiceOffer[]>(`/service-requests/${requestId}/offers`);
}

export async function submitServiceOffer(
  requestId: string,
  body: { price_cents: number; included_work: string; excluded_work?: string; estimated_days?: number }
) {
  return apiFetch<ServiceOffer>(`/service-requests/${requestId}/offers`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function acceptServiceOffer(offerId: string) {
  return apiFetch<ServiceJob>(`/offers/${offerId}/accept`, { method: "POST" });
}

export type ServiceJobEvent = {
  event_type: string;
  summary: string;
  created_at: string;
};

export type ServiceJob = {
  id: string;
  request_id: string;
  request_title: string;
  status: string;
  price_cents_snapshot: number;
  included_work_snapshot: string;
  provider_name: string;
  customer_name: string;
  is_provider_view: boolean;
  hold_expires_at: string | null;
  paid_at: string | null;
  started_at: string | null;
  timeline: ServiceJobEvent[];
  conversation_id: string | null;
  has_review: boolean;
  created_at: string;
};

export async function fetchMyServiceJobs() {
  return apiFetch<ServiceJob[]>("/me/service-jobs");
}

export async function startServiceJob(jobId: string) {
  return apiFetch<ServiceJob>(`/service-jobs/${jobId}/start`, { method: "POST" });
}

export async function submitServiceCompletion(jobId: string) {
  return apiFetch<ServiceJob>(`/service-jobs/${jobId}/submit-completion`, { method: "POST" });
}

export async function confirmServiceCompletion(jobId: string) {
  return apiFetch<ServiceJob>(`/service-jobs/${jobId}/confirm-completion`, { method: "POST" });
}

export async function createServicePaymentIntent(jobId: string) {
  return apiFetch<{
    payment_id: string;
    service_job_id: string;
    amount_cents: number;
  }>(`/service-jobs/${jobId}/payment-intent`, { method: "POST" });
}

export async function sandboxPayServiceJob(jobId: string, paymentId: string) {
  return apiFetch(`/service-jobs/${jobId}/sandbox-pay?payment_id=${encodeURIComponent(paymentId)}`, {
    method: "POST",
  });
}

export async function submitAssistanceReview(jobId: string, body: { rating: number; comment: string }) {
  return apiFetch(`/service-jobs/${jobId}/review`, { method: "POST", body: JSON.stringify(body) });
}

export type ConversationMessage = {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  created_at: string;
  is_mine: boolean;
};

export type ConversationSummary = {
  id: string;
  kind?: "service_job" | "rental_booking";
  service_job_id: string | null;
  rental_booking_id?: string | null;
  job_title: string;
  job_status: string;
  partner_name: string;
  last_message_preview: string | null;
  messages: ConversationMessage[];
};

export type ConversationThread = ConversationSummary;

export async function fetchMyConversations() {
  return apiFetch<ConversationSummary[]>("/me/conversations");
}

export async function fetchConversation(conversationId: string) {
  return apiFetch<ConversationThread>(`/conversations/${conversationId}`);
}

export async function fetchRentalBookingConversation(bookingId: string) {
  return apiFetch<ConversationThread>(`/rental-bookings/${bookingId}/conversation`);
}

export type UserSessionRow = {
  id: string;
  user_agent: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
};

export async function fetchMySessions() {
  return apiFetch<UserSessionRow[]>("/me/sessions");
}

export async function revokeSession(sessionId: string) {
  await apiFetch<void>(`/me/sessions/${sessionId}`, { method: "DELETE" });
}

export async function revokeOtherSessions() {
  await apiFetch<void>("/me/sessions/revoke-others", { method: "POST" });
}

export type SupervisionRow = {
  id: string;
  trainee_id: string;
  supervisor_id: string;
  trainee_name: string;
  supervisor_name: string;
  status: string;
  trainee_note: string | null;
  created_at: string;
  responded_at: string | null;
};

export type EndorsementRow = {
  id: string;
  trainee_name: string;
  category_name: string | null;
  note: string;
  created_at: string;
};

export async function enrollAsTrainee() {
  await apiFetch<void>("/me/supervision/trainee/enroll", { method: "POST" });
}

export async function requestSupervisor(body: { supervisor_email: string; trainee_note?: string }) {
  return apiFetch<SupervisionRow>("/me/supervision/request", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMySupervision() {
  return apiFetch<SupervisionRow[]>("/me/supervision");
}

export async function fetchPendingSupervision() {
  return apiFetch<SupervisionRow[]>("/me/supervision/pending");
}

export async function acceptSupervisionRequest(relationshipId: string) {
  return apiFetch<SupervisionRow>(`/me/supervision/requests/${relationshipId}`, {
    method: "POST",
    body: JSON.stringify({ accept: true }),
  });
}

export async function declineSupervisionRequest(relationshipId: string) {
  return apiFetch<SupervisionRow>(`/me/supervision/requests/${relationshipId}`, {
    method: "POST",
    body: JSON.stringify({ accept: false }),
  });
}

export async function createSupervisionEndorsement(body: {
  trainee_id: string;
  category_slug?: string;
  note: string;
}) {
  return apiFetch<EndorsementRow>("/me/supervision/endorsements", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchMyEndorsements() {
  return apiFetch<EndorsementRow[]>("/me/supervision/endorsements");
}

export async function sendConversationMessage(conversationId: string, body: string) {
  return apiFetch<ConversationMessage>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export type ProviderCategoryStatus = {
  slug: string;
  name: string;
  verification_status: string;
};

export async function fetchMyPortfolioCategories() {
  return apiFetch<ProviderCategoryStatus[]>("/me/provider-portfolio/categories");
}

export type SkillVerificationRow = {
  portfolio_user_id: string;
  category_id: string;
  category_slug: string;
  category_name: string;
  provider_name: string;
  provider_headline: string;
  verification_status: string;
  admin_note: string | null;
  reviewed_at: string | null;
};

export async function fetchPendingSkillVerifications() {
  return apiFetch<SkillVerificationRow[]>("/admin/skill-verifications?status=pending");
}

export async function approveSkillVerification(portfolioUserId: string, categoryId: string, note: string) {
  return apiFetch<SkillVerificationRow>(
    `/admin/skill-verifications/${portfolioUserId}/${categoryId}`,
    { method: "POST", body: JSON.stringify({ approve: true, note }) }
  );
}

export async function rejectSkillVerification(portfolioUserId: string, categoryId: string, note: string) {
  return apiFetch<SkillVerificationRow>(
    `/admin/skill-verifications/${portfolioUserId}/${categoryId}`,
    { method: "POST", body: JSON.stringify({ approve: false, note }) }
  );
}

export type AppNotification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  link_path: string | null;
  read_at: string | null;
  created_at: string;
};

export async function fetchNotifications() {
  return apiFetch<AppNotification[]>("/me/notifications");
}

export async function fetchUnreadNotificationCount() {
  return apiFetch<{ count: number }>("/me/notifications/unread-count");
}

export async function markNotificationRead(id: string) {
  return apiFetch<AppNotification>(`/me/notifications/${id}/read`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ count: number }>("/me/notifications/read-all", { method: "POST" });
}

export async function fetchWishlist() {
  return apiFetch<ListingPublic[]>("/me/wishlist");
}

export async function fetchWishlistIds() {
  return apiFetch<string[]>("/me/wishlist/ids");
}

export async function saveListing(itemId: string) {
  await apiFetch<void>(`/me/wishlist/${itemId}`, { method: "PUT" });
}

export async function unsaveListing(itemId: string) {
  await apiFetch<void>(`/me/wishlist/${itemId}`, { method: "DELETE" });
}

export type CommunityPost = {
  id: string;
  kind: string;
  title: string;
  body: string;
  area_label: string;
  author_name: string;
  is_mine: boolean;
  linked_listing_id: string | null;
  linked_listing_title: string | null;
  helpful_count: number;
  thanks_count: number;
  my_reaction: string | null;
  comment_count: number;
  created_at: string;
};

export type CommunityComment = {
  id: string;
  author_name: string;
  body: string;
  is_mine: boolean;
  created_at: string;
};

export type CommunityPostDetail = CommunityPost & { comments: CommunityComment[] };

export async function fetchCommunityPosts(params?: {
  kind?: string;
  latitude?: number;
  longitude?: number;
  radius_km?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.kind) qs.set("kind", params.kind);
  if (params?.latitude != null) qs.set("latitude", String(params.latitude));
  if (params?.longitude != null) qs.set("longitude", String(params.longitude));
  if (params?.radius_km != null) qs.set("radius_km", String(params.radius_km));
  const q = qs.toString();
  return apiFetch<CommunityPost[]>(`/community/posts${q ? `?${q}` : ""}`);
}

export type UserSettings = {
  notify_rentals: boolean;
  notify_assistance: boolean;
  notify_messages: boolean;
  notify_community: boolean;
  preferred_locale: string;
  default_latitude: number | null;
  default_longitude: number | null;
  default_radius_km: number;
};

export async function fetchUserSettings() {
  return apiFetch<UserSettings>("/me/settings");
}

export async function updateUserSettings(patch: Partial<UserSettings> & Pick<UserSettings, keyof UserSettings>) {
  return apiFetch<UserSettings>("/me/settings", { method: "PATCH", body: JSON.stringify(patch) });
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await apiFetch<void>("/me/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export type IdentityStatus = {
  user_id: string;
  document_type: string;
  document_reference: string;
  user_note: string | null;
  status: string;
  admin_note: string | null;
  submitted_at: string;
  reviewed_at: string | null;
};

export async function fetchIdentity() {
  return apiFetch<IdentityStatus | null>("/me/identity");
}

export async function submitIdentity(body: {
  document_type: string;
  document_reference: string;
  user_note?: string;
}) {
  return apiFetch<IdentityStatus>("/me/identity", { method: "POST", body: JSON.stringify(body) });
}

export type DisputeRow = {
  id: string;
  subject_type: string;
  subject_id: string;
  opened_by: string;
  reason: string;
  status: string;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchMyDisputes() {
  return apiFetch<DisputeRow[]>("/disputes/mine");
}

export async function createDispute(body: {
  subject_type: "rental_booking" | "service_job";
  subject_id: string;
  reason: string;
}) {
  return apiFetch<DisputeRow>("/disputes", { method: "POST", body: JSON.stringify(body) });
}

export type IdentityAdminRow = {
  user_id: string;
  display_name: string;
  email: string;
  document_type: string;
  document_reference: string;
  user_note: string | null;
  status: string;
  submitted_at: string;
};

export async function fetchPendingIdentityVerifications() {
  return apiFetch<IdentityAdminRow[]>("/admin/identity-verifications?status=pending");
}

export async function approveIdentity(userId: string, note?: string) {
  return apiFetch<IdentityStatus>(`/admin/identity-verifications/${userId}`, {
    method: "POST",
    body: JSON.stringify({ approve: true, note }),
  });
}

export async function rejectIdentity(userId: string, note: string) {
  return apiFetch<IdentityStatus>(`/admin/identity-verifications/${userId}`, {
    method: "POST",
    body: JSON.stringify({ approve: false, note }),
  });
}

export async function fetchAdminDisputes(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<DisputeRow[]>(`/admin/disputes${q}`);
}

export async function resolveAdminDispute(
  disputeId: string,
  status: string,
  resolutionNotes: string,
  depositOutcome?: "release_renter" | "release_owner"
) {
  return apiFetch<DisputeRow>(`/admin/disputes/${disputeId}`, {
    method: "PATCH",
    body: JSON.stringify({
      status,
      resolution_notes: resolutionNotes,
      deposit_outcome: depositOutcome,
    }),
  });
}

export type AuditRow = {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export async function fetchAuditLog(limit = 100) {
  return apiFetch<AuditRow[]>(`/admin/audit-log?limit=${limit}`);
}

export async function createCommunityPost(body: {
  kind: string;
  title: string;
  body: string;
  area_label: string;
  latitude?: number;
  longitude?: number;
  linked_listing_id?: string;
}) {
  return apiFetch<CommunityPost>("/community/posts", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchCommunityPostDetail(postId: string) {
  return apiFetch<CommunityPostDetail>(`/community/posts/${postId}`);
}

export async function addCommunityComment(postId: string, body: string) {
  return apiFetch<CommunityComment>(`/community/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export async function setCommunityReaction(postId: string, reaction: "helpful" | "thanks") {
  return apiFetch<CommunityPost>(`/community/posts/${postId}/reactions`, {
    method: "POST",
    body: JSON.stringify({ reaction }),
  });
}

export async function fetchAdminCommunityPosts() {
  return apiFetch<CommunityPost[]>("/admin/community/posts");
}

export async function hideCommunityPost(postId: string, reason: string) {
  return apiFetch<CommunityPost>(`/admin/community/posts/${postId}/hide`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
