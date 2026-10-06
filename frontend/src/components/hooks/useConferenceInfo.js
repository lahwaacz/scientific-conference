import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import { conferenceTitle } from "../../utils/conferenceTitle";

export function useConferenceInfo() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    fetch(buildApiUrl("/api/conference-info/"))
      .then((r) => r.json())
      .then(setInfo)
      .catch(() => {});
  }, []);

  // Keep the browser tab title in sync with the loaded conference.
  useEffect(() => {
    if (info) {
      document.title = conferenceTitle(info) || document.title;
    }
  }, [info]);

  return info;
}
