export const en = {
  tagline: "Your neighbourhood, connected.",
  nav_explore_rentals: "Explore rentals",
  nav_find_services: "Find services",
  nav_activity: "My activity",
  nav_messages: "Messages",
  nav_notifications: "Notifications",
  nav_community: "Community",
  nav_disputes: "Disputes",
  nav_mentorship: "Mentorship",
  nav_listings: "My listings",
  nav_saved: "Saved items",
  nav_profile: "My profile",
  nav_settings: "Settings",
  nav_admin: "Administration",
  mode_rental: "Rental",
  mode_assistance: "Assistance",
  sign_out: "Sign out",
  escrow_held: "Deposit held in escrow",
  escrow_released_renter: "Deposit returned to you",
  escrow_released_owner: "Deposit paid to owner",
} as const;

export type MessageKey = keyof typeof en;