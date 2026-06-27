import { api } from "./client";

export interface ThemePreferences {
  mode: "light" | "dark";
  accent: "teal" | "blue" | "rose";
  density: "comfortable" | "compact";
}

export async function getPreferences(): Promise<ThemePreferences> {
  return api<ThemePreferences>("/api/v1/account/preferences");
}

export async function updatePreferences(
  prefs: ThemePreferences,
): Promise<ThemePreferences> {
  return api<ThemePreferences>("/api/v1/account/preferences", {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}
