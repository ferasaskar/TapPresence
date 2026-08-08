import { createContext, useContext } from "react";

// Provides analytics tracking to profile building-blocks. Default is a no-op
// so the admin live-preview never records events.
export const ProfileContext = createContext({ track: () => {} });

export const useProfile = () => useContext(ProfileContext);
