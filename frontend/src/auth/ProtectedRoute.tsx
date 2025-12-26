import { Navigate } from "react-router-dom";
import { useAuthContext } from "./AuthContext";

export const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { user, loading } = useAuthContext();

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  return children;
};
