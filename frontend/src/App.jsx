import React, { useEffect, useState } from "react";
import { api } from "./api";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/")
      .then((res) => setMessage(res.data.status || JSON.stringify(res.data)))
      .catch((err) => setMessage("Error connecting to backend"));
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
      <h1 className="text-3xl font-bold text-blue-600 mb-4">POSTIKA Frontend is Live!</h1>
      <p className="text-xl">{message}</p>
    </div>
  );
}

export default App;
