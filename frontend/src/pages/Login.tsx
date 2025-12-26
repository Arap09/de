import { useState } from "react";
import { useAuthContext } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuthContext();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          login(email, password);
        }}
        className="w-96 p-6 border rounded"
      >
        <h1 className="text-xl mb-4">Login</h1>
        <input className="input" placeholder="Email" onChange={e => setEmail(e.target.value)} />
        <input className="input mt-2" type="password" placeholder="Password" onChange={e => setPassword(e.target.value)} />
        <button className="btn mt-4 w-full">Login</button>
      </form>
    </div>
  );
}
