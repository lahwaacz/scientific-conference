import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";

export function useConferenceInfo() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    fetch(buildApiUrl("/api/conference-info/"))
      .then((r) => r.json())
      .then(setInfo)
      .catch(() => {});
  }, []);

  return info;
}
