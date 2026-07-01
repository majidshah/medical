import { api } from "./client";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccountResponse {
  id: string;
  email: string;
  roles: string[];
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return api<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  email: string,
  password: string,
): Promise<AccountResponse> {
  return api<AccountResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<AccountResponse> {
  return api<AccountResponse>("/api/v1/auth/me");
}
