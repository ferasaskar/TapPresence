import { createContext, useContext } from "react";

// Provides analytics tracking to profile building-blocks. Default is a no-op
// so the admin live-preview never records events. `publicView` is false by
// default so viewport-fixed UI (e.g. sticky CTA bar) only renders on the real
// public profile page, never inside editor/showcase previews.
export const ProfileContext = createContext({ track: () => {}, publicView: false });

export const useProfile = () => useContext(ProfileContext);
