import api from "./axios";
import { LoginPayload, RegisterPayload, User } from "../types/auth";

export const login = async (payload: LoginPayload) => {
  const { data } = await api.post("/auth/login", payload);
  return data;
};

export const register = async (payload: RegisterPayload) => {
  const { data } = await api.post("/auth/register", payload);
  return data;
};

export const fetchMe = async (): Promise<User> => {
  const { data } = await api.get("/auth/me");
  return data;
};
