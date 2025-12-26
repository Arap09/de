import { useAuthContext } from "../auth/AuthContext";

export default function Dashboard() {
  const { user, logout } = useAuthContext();

  return (
    <div className="p-8">
      <h1 className="text-2xl">Welcome, {user?.email}</h1>
      <button onClick={logout} className="btn mt-4">
        Logout
      </button>
    </div>
  );
}
