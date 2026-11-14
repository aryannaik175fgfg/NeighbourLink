import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { hasRole } = useAuth();
  if (!hasRole("administrator")) {
    return <Navigate to="/app/explore" replace />;
  }
  return children;
}
