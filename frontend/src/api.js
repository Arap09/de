// src/api.js
import axios from "axios";

// Use the backend URL from the .env file
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const api = axios.create({
  baseURL: API_BASE_URL,
});
